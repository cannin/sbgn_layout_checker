//! Orthogonal SBGN arc routing over immutable glyph geometry.

use std::collections::{BTreeMap, HashMap, HashSet};
use std::fs::File;
use std::io::{BufReader, BufWriter};
use std::path::Path;

use anyhow::{Context, Result, anyhow, ensure};
use libavoid::{
    ConnEnd, ConnRef, ConnType, Point as AvoidPoint, Rectangle, Router, RoutingOption,
    RoutingParameter,
};
use thiserror::Error;
use xmltree::{Element, EmitterConfig, XMLNode};

// libavoid's C++ core may return boundary coordinates about 1e-6 apart.
const GEOMETRY_EPSILON: f64 = 1e-5;

/// One two-dimensional point in SBGN source coordinates.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Point {
    /// Horizontal coordinate.
    pub x: f64,
    /// Vertical coordinate.
    pub y: f64,
}

impl Point {
    /// Construct a point from source coordinates.
    pub fn new(x: f64, y: f64) -> Self {
        Self { x, y }
    }
}

/// Immutable SBGN glyph bounding box.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct BoundingBox {
    /// Left coordinate.
    pub x: f64,
    /// Top coordinate.
    pub y: f64,
    /// Width.
    pub width: f64,
    /// Height.
    pub height: f64,
}

impl BoundingBox {
    /// Return the center of the bounding box.
    pub fn center(self) -> Point {
        Point::new(self.x + self.width / 2.0, self.y + self.height / 2.0)
    }

    /// Return a box expanded by the requested clearance.
    pub fn expanded(self, clearance: f64) -> Self {
        Self {
            x: self.x - clearance,
            y: self.y - clearance,
            width: self.width + 2.0 * clearance,
            height: self.height + 2.0 * clearance,
        }
    }
}

/// Graph node used only as a fixed routing obstacle.
#[derive(Clone, Debug, PartialEq)]
pub struct Node {
    /// Stable SBGN glyph ID.
    pub id: String,
    /// SBGN glyph class.
    pub class_name: String,
    /// Immutable glyph geometry.
    pub bbox: BoundingBox,
    /// Orientation attribute, when present.
    pub orientation: Option<String>,
    /// Parent glyph ID for nested auxiliary glyphs.
    pub parent_id: Option<String>,
}

/// Routable SBGN arc with fixed terminals.
#[derive(Clone, Debug, PartialEq)]
pub struct Edge {
    /// Stable SBGN arc ID.
    pub id: String,
    /// SBGN arc class.
    pub class_name: String,
    /// Original source reference.
    pub source: String,
    /// Original target reference.
    pub target: String,
    /// Owning source glyph, resolving a port reference when possible.
    pub source_node_id: Option<String>,
    /// Owning target glyph, resolving a port reference when possible.
    pub target_node_id: Option<String>,
    /// Explicit SBGN start coordinate, kept fixed.
    pub start: Point,
    /// Explicit SBGN end coordinate, kept fixed.
    pub end: Point,
    /// Existing intermediate bend points.
    pub bends: Vec<Point>,
}

/// Routing-only graph separated from the XML document model.
#[derive(Clone, Debug, PartialEq)]
pub struct Graph {
    /// Fixed glyph obstacles.
    pub nodes: Vec<Node>,
    /// Arcs with fixed endpoints.
    pub edges: Vec<Edge>,
}

/// Conservative libavoid routing configuration.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct RoutingConfig {
    /// Clearance between routes and non-container glyph obstacles.
    pub shape_buffer_distance: f64,
    /// Desired spacing between nudged orthogonal segments.
    pub ideal_nudging_distance: f64,
    /// Cost for adding route segments.
    pub segment_penalty: f64,
    /// Cost for crossing another connector.
    pub crossing_penalty: f64,
}

impl Default for RoutingConfig {
    fn default() -> Self {
        Self {
            shape_buffer_distance: 4.0,
            ideal_nudging_distance: 4.0,
            segment_penalty: 10.0,
            crossing_penalty: 200.0,
        }
    }
}

/// Failures returned by the isolated routing layer.
#[derive(Debug, Error)]
pub enum RoutingError {
    /// libavoid did not return a display route for an arc.
    #[error("libavoid returned no display route for arc {0}")]
    MissingRoute(String),
    /// libavoid moved an explicitly fixed terminal.
    #[error(
        "libavoid changed a fixed endpoint for arc {edge_id}: expected {expected_start:?} -> {expected_end:?}, got {actual_start:?} -> {actual_end:?}"
    )]
    EndpointChanged {
        /// Stable SBGN arc ID.
        edge_id: String,
        /// Fixed source terminal.
        expected_start: Point,
        /// Fixed target terminal.
        expected_end: Point,
        /// First returned route point.
        actual_start: Point,
        /// Last returned route point.
        actual_end: Point,
    },
    /// libavoid returned a diagonal segment in orthogonal mode.
    #[error("libavoid returned a non-orthogonal route for arc {edge_id}: {points:?}")]
    NonOrthogonalRoute {
        /// Stable SBGN arc ID.
        edge_id: String,
        /// Simplified returned route.
        points: Vec<Point>,
    },
    /// Graph node geometry changed during route calculation.
    #[error("node geometry changed during edge routing")]
    NodeGeometryChanged,
    /// A routed segment enters an unrelated node obstacle.
    #[error("route for arc {edge_id} enters unrelated obstacle {node_id}: {points:?}")]
    ObstacleIntersection {
        /// Stable SBGN arc ID.
        edge_id: String,
        /// Stable SBGN glyph ID.
        node_id: String,
        /// Routed points returned for diagnosis.
        points: Vec<Point>,
    },
}

/// Route calculation result indexed by stable SBGN arc ID.
pub type EdgeRoutes = BTreeMap<String, Vec<Point>>;

/// Parsed SBGN document plus its routing-only graph.
pub struct SbgnDocument {
    root: Element,
    graph: Graph,
}

impl SbgnDocument {
    /// Read SBGN-ML and extract immutable node geometry and arc terminals.
    pub fn read(path: &Path) -> Result<Self> {
        let file = File::open(path)
            .with_context(|| format!("failed to open SBGN input {}", path.display()))?;
        let root = Element::parse(BufReader::new(file))
            .with_context(|| format!("failed to parse SBGN XML {}", path.display()))?;
        let graph = graph_from_xml(&root)?;
        Ok(Self { root, graph })
    }

    /// Access the routing-only graph.
    pub fn graph(&self) -> &Graph {
        &self.graph
    }

    /// Compute and apply arc bend points without touching other XML geometry.
    pub fn route_arcs(&mut self, config: &RoutingConfig) -> Result<EdgeRoutes> {
        let graph_geometry_before = snapshot_graph_geometry(&self.graph);
        let xml_geometry_before = snapshot_xml_geometry(&self.root);
        let semantics_before = semantic_fingerprint(&self.root)?;

        let routes = compute_edge_routes(&self.graph, config)?;
        if graph_geometry_before != snapshot_graph_geometry(&self.graph) {
            return Err(RoutingError::NodeGeometryChanged.into());
        }
        apply_edge_routes(&mut self.root, &routes);
        ensure!(
            xml_geometry_before == snapshot_xml_geometry(&self.root),
            "glyph geometry changed while applying edge routes"
        );
        ensure!(
            semantics_before == semantic_fingerprint(&self.root)?,
            "routing changed SBGN content outside arc bend points"
        );
        Ok(routes)
    }

    /// Write the routed SBGN-ML document.
    pub fn write(&self, path: &Path) -> Result<()> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)
                .with_context(|| format!("failed to create {}", parent.display()))?;
        }
        let file = File::create(path)
            .with_context(|| format!("failed to create SBGN output {}", path.display()))?;
        self.root
            .write_with_config(
                BufWriter::new(file),
                EmitterConfig::new()
                    .perform_indent(true)
                    .write_document_declaration(true),
            )
            .with_context(|| format!("failed to write SBGN XML {}", path.display()))?;
        Ok(())
    }
}

/// Compute orthogonal edge routes without mutating graph geometry.
pub fn compute_edge_routes(
    graph: &Graph,
    config: &RoutingConfig,
) -> std::result::Result<EdgeRoutes, RoutingError> {
    let geometry_before = snapshot_graph_geometry(graph);
    let mut router = Router::new(ConnType::Orthogonal as u32);
    router.set_transaction_use(true);
    router.set_routing_parameter(
        RoutingParameter::ShapeBufferDistance,
        config.shape_buffer_distance,
    );
    router.set_routing_parameter(
        RoutingParameter::IdealNudgingDistance,
        config.ideal_nudging_distance,
    );
    router.set_routing_parameter(RoutingParameter::SegmentPenalty, config.segment_penalty);
    router.set_routing_parameter(RoutingParameter::CrossingPenalty, config.crossing_penalty);
    router.set_routing_option(RoutingOption::NudgeOrthogonalRoutes, false);
    router.set_routing_option(RoutingOption::PenaliseOrthogonalSharedPathsAtConnEnds, true);

    let node_by_id = graph
        .nodes
        .iter()
        .map(|node| (node.id.as_str(), node))
        .collect::<HashMap<_, _>>();
    for (index, node) in graph
        .nodes
        .iter()
        .filter(|node| is_routing_obstacle(node))
        .enumerate()
    {
        let center = node.bbox.center();
        let rectangle = Rectangle::new(
            AvoidPoint::new(center.x, center.y),
            node.bbox.width,
            node.bbox.height,
        );
        let shape_id = stable_numeric_id(index)?;
        router.add_shape(rectangle.into(), shape_id);
    }

    let mut connector_ids = Vec::new();
    let mut routes = EdgeRoutes::new();
    for (index, edge) in graph.edges.iter().enumerate() {
        if points_equal(edge.start, edge.end) {
            routes.insert(edge.id.clone(), vec![edge.start]);
            continue;
        }
        // libavoid object IDs share a router-wide namespace, so connector IDs
        // must never collide with shape IDs.
        let connector_id = stable_numeric_id(graph.nodes.len() + index)?;
        let routing_start = escape_endpoint(
            edge.start,
            edge.source_node_id.as_deref(),
            &node_by_id,
            config.shape_buffer_distance,
        );
        let routing_end = escape_endpoint(
            edge.end,
            edge.target_node_id.as_deref(),
            &node_by_id,
            config.shape_buffer_distance,
        );
        let source = ConnEnd::new(AvoidPoint::new(routing_start.x, routing_start.y));
        let target = ConnEnd::new(AvoidPoint::new(routing_end.x, routing_end.y));
        let mut connector = ConnRef::with_endpoints(connector_id, source, target);
        connector.set_routing_type(ConnType::Orthogonal);
        connector.set_hate_crossings(true);
        router.add_connector(connector);
        connector_ids.push((
            &edge.id,
            connector_id,
            routing_start,
            routing_end,
            edge.start,
            edge.end,
        ));
    }

    router.process_transaction();
    for (edge_id, connector_id, routing_start, routing_end, fixed_start, fixed_end) in connector_ids
    {
        let connector = router
            .get_connector(connector_id)
            .ok_or_else(|| RoutingError::MissingRoute(edge_id.clone()))?;
        let display_route = connector
            .display_route()
            .ok_or_else(|| RoutingError::MissingRoute(edge_id.clone()))?;
        let points = display_route
            .points()
            .map(|point| Point::new(point.x, point.y))
            .collect::<Vec<_>>();
        if points.is_empty() {
            return Err(RoutingError::MissingRoute(edge_id.clone()));
        }
        let edge = graph
            .edges
            .iter()
            .find(|edge| edge.id == *edge_id)
            .expect("connector maps to an existing edge");
        // The current libavoid-rust port can return a direct diagonal fallback
        // when no visibility-graph route is found. Convert only those fallback
        // segments to the less obstructed of their two Manhattan alternatives.
        let points = orthogonalize_fallback_segments(
            &points,
            edge,
            &graph.nodes,
            config.shape_buffer_distance,
        );
        let points = restore_fixed_endpoints(&points, routing_start, routing_end);
        let mut points = restore_fixed_endpoints(&points, fixed_start, fixed_end);
        if !points_equal(points[0], fixed_start)
            || !points_equal(*points.last().expect("nonempty route"), fixed_end)
        {
            return Err(RoutingError::EndpointChanged {
                edge_id: edge_id.clone(),
                expected_start: fixed_start,
                expected_end: fixed_end,
                actual_start: points.first().copied().unwrap_or(fixed_start),
                actual_end: points.last().copied().unwrap_or(fixed_end),
            });
        }
        points = simplify_route(&points);
        if !route_is_orthogonal(&points) {
            return Err(RoutingError::NonOrthogonalRoute {
                edge_id: edge_id.clone(),
                points,
            });
        }
        if let Some(node) = first_intersected_unrelated_node(&points, edge, &graph.nodes, 0.0) {
            return Err(RoutingError::ObstacleIntersection {
                edge_id: edge_id.clone(),
                node_id: node.id.clone(),
                points,
            });
        }
        routes.insert(edge_id.clone(), points);
    }

    if geometry_before != snapshot_graph_geometry(graph) {
        return Err(RoutingError::NodeGeometryChanged);
    }
    Ok(routes)
}

fn orthogonalize_fallback_segments(
    points: &[Point],
    edge: &Edge,
    nodes: &[Node],
    clearance: f64,
) -> Vec<Point> {
    let mut orthogonal = vec![points[0]];
    for endpoint in points.iter().copied().skip(1) {
        let start = *orthogonal.last().expect("route has a first point");
        if !approximately_equal(start.x, endpoint.x) && !approximately_equal(start.y, endpoint.y) {
            let horizontal_then_vertical = Point::new(endpoint.x, start.y);
            let vertical_then_horizontal = Point::new(start.x, endpoint.y);
            let horizontal_score = elbow_obstacle_score(
                start,
                horizontal_then_vertical,
                endpoint,
                edge,
                nodes,
                clearance,
            );
            let vertical_score = elbow_obstacle_score(
                start,
                vertical_then_horizontal,
                endpoint,
                edge,
                nodes,
                clearance,
            );
            if horizontal_score <= vertical_score {
                orthogonal.push(horizontal_then_vertical);
            } else {
                orthogonal.push(vertical_then_horizontal);
            }
        }
        orthogonal.push(endpoint);
    }
    simplify_route(&orthogonal)
}

fn elbow_obstacle_score(
    start: Point,
    elbow: Point,
    end: Point,
    edge: &Edge,
    nodes: &[Node],
    clearance: f64,
) -> usize {
    nodes
        .iter()
        .filter(|node| is_routing_obstacle(node))
        .filter(|node| !is_terminal_related_node(node, edge, nodes))
        .filter(|node| {
            let bbox = node.bbox.expanded(clearance);
            segment_enters_box(start, elbow, bbox) || segment_enters_box(elbow, end, bbox)
        })
        .count()
}

fn escape_endpoint(
    point: Point,
    node_id: Option<&str>,
    nodes: &HashMap<&str, &Node>,
    clearance: f64,
) -> Point {
    let Some(node) = node_id.and_then(|id| nodes.get(id)).copied() else {
        return point;
    };
    let expanded = node
        .bbox
        .expanded(clearance.max(0.0) + GEOMETRY_EPSILON * 10.0);
    let right = expanded.x + expanded.width;
    let bottom = expanded.y + expanded.height;
    if point.x <= expanded.x || point.x >= right || point.y <= expanded.y || point.y >= bottom {
        return point;
    }
    let distances = [
        (point.x - expanded.x, Point::new(expanded.x, point.y)),
        (right - point.x, Point::new(right, point.y)),
        (point.y - expanded.y, Point::new(point.x, expanded.y)),
        (bottom - point.y, Point::new(point.x, bottom)),
    ];
    distances
        .into_iter()
        .min_by(|first, second| first.0.total_cmp(&second.0))
        .map(|(_, endpoint)| endpoint)
        .unwrap_or(point)
}

fn restore_fixed_endpoints(points: &[Point], fixed_start: Point, fixed_end: Point) -> Vec<Point> {
    let mut restored = Vec::with_capacity(points.len() + 4);
    let actual_start = points[0];
    restored.push(fixed_start);
    if !points_equal(fixed_start, actual_start) {
        if !approximately_equal(fixed_start.x, actual_start.x)
            && !approximately_equal(fixed_start.y, actual_start.y)
        {
            restored.push(Point::new(fixed_start.x, actual_start.y));
        }
        restored.push(actual_start);
    }
    restored.extend(points.iter().copied().skip(1));

    let actual_end = *restored.last().expect("route has at least one point");
    if !points_equal(actual_end, fixed_end) {
        if !approximately_equal(actual_end.x, fixed_end.x)
            && !approximately_equal(actual_end.y, fixed_end.y)
        {
            restored.push(Point::new(actual_end.x, fixed_end.y));
        }
        restored.push(fixed_end);
    }
    restored
}

fn stable_numeric_id(index: usize) -> std::result::Result<u32, RoutingError> {
    u32::try_from(index + 1).map_err(|_| RoutingError::NodeGeometryChanged)
}

fn is_routing_obstacle(node: &Node) -> bool {
    node.class_name != "compartment" && node.bbox.width > 0.0 && node.bbox.height > 0.0
}

/// Remove consecutive duplicates and unnecessary orthogonal collinear points.
pub fn simplify_route(points: &[Point]) -> Vec<Point> {
    let mut deduplicated = Vec::new();
    for point in points {
        if deduplicated
            .last()
            .is_none_or(|previous| !points_equal(*previous, *point))
        {
            deduplicated.push(*point);
        }
    }
    if deduplicated.len() < 3 {
        return deduplicated;
    }

    let mut simplified = vec![deduplicated[0]];
    for index in 1..deduplicated.len() - 1 {
        let previous = *simplified.last().expect("route has a first point");
        let current = deduplicated[index];
        let next = deduplicated[index + 1];
        let vertical =
            approximately_equal(previous.x, current.x) && approximately_equal(current.x, next.x);
        let horizontal =
            approximately_equal(previous.y, current.y) && approximately_equal(current.y, next.y);
        if !vertical && !horizontal {
            simplified.push(current);
        }
    }
    simplified.push(*deduplicated.last().expect("route has a last point"));
    simplified
}

/// Return whether every route segment is horizontal or vertical.
pub fn route_is_orthogonal(points: &[Point]) -> bool {
    points.windows(2).all(|segment| {
        approximately_equal(segment[0].x, segment[1].x)
            || approximately_equal(segment[0].y, segment[1].y)
    })
}

/// Return whether a segment enters a bounding box's open interior.
pub fn segment_enters_box(start: Point, end: Point, bbox: BoundingBox) -> bool {
    let x_interval = open_axis_interval(start.x, end.x - start.x, bbox.x, bbox.x + bbox.width);
    let y_interval = open_axis_interval(start.y, end.y - start.y, bbox.y, bbox.y + bbox.height);
    let (Some((x_low, x_high)), Some((y_low, y_high))) = (x_interval, y_interval) else {
        return false;
    };
    let lower = 0.0_f64.max(x_low).max(y_low);
    let upper = 1.0_f64.min(x_high).min(y_high);
    upper - lower > GEOMETRY_EPSILON
}

fn open_axis_interval(start: f64, delta: f64, lower: f64, upper: f64) -> Option<(f64, f64)> {
    if upper - lower <= GEOMETRY_EPSILON {
        return None;
    }
    if delta.abs() <= GEOMETRY_EPSILON {
        return (lower < start && start < upper).then_some((f64::NEG_INFINITY, f64::INFINITY));
    }
    let first = (lower - start) / delta;
    let second = (upper - start) / delta;
    Some((first.min(second), first.max(second)))
}

fn points_equal(first: Point, second: Point) -> bool {
    approximately_equal(first.x, second.x) && approximately_equal(first.y, second.y)
}

fn approximately_equal(first: f64, second: f64) -> bool {
    (first - second).abs() <= GEOMETRY_EPSILON
}

fn snapshot_graph_geometry(graph: &Graph) -> Vec<(String, BoundingBox, Option<String>)> {
    graph
        .nodes
        .iter()
        .map(|node| (node.id.clone(), node.bbox, node.orientation.clone()))
        .collect()
}

fn direct_child<'a>(element: &'a Element, name: &str) -> Option<&'a Element> {
    element.children.iter().find_map(|child| match child {
        XMLNode::Element(child) if child.name == name => Some(child),
        _ => None,
    })
}

fn parse_number(element: &Element, attribute: &str) -> Result<f64> {
    element
        .attributes
        .get(attribute)
        .ok_or_else(|| anyhow!("{} missing {} attribute", element.name, attribute))?
        .parse::<f64>()
        .with_context(|| format!("invalid {} coordinate", element.name))
}

fn parse_point(element: &Element) -> Result<Point> {
    Ok(Point::new(
        parse_number(element, "x")?,
        parse_number(element, "y")?,
    ))
}

fn parse_bbox(element: &Element) -> Result<BoundingBox> {
    Ok(BoundingBox {
        x: parse_number(element, "x")?,
        y: parse_number(element, "y")?,
        width: parse_number(element, "w")?,
        height: parse_number(element, "h")?,
    })
}

fn graph_from_xml(root: &Element) -> Result<Graph> {
    let mut nodes = Vec::new();
    let mut port_owners = HashMap::new();
    let mut seen_node_ids = HashSet::new();
    collect_glyphs(root, None, &mut nodes, &mut port_owners, &mut seen_node_ids)?;

    let mut edges = Vec::new();
    let mut seen_edge_ids = HashSet::new();
    collect_arcs(root, &port_owners, &mut edges, &mut seen_edge_ids)?;
    Ok(Graph { nodes, edges })
}

fn collect_glyphs(
    element: &Element,
    parent_glyph_id: Option<String>,
    nodes: &mut Vec<Node>,
    port_owners: &mut HashMap<String, String>,
    seen_ids: &mut HashSet<String>,
) -> Result<()> {
    let mut child_parent_id = parent_glyph_id.clone();
    if element.name == "glyph" {
        let id = element.attributes.get("id").cloned().unwrap_or_default();
        if !id.is_empty() {
            child_parent_id = Some(id.clone());
        }
        if !id.is_empty() && seen_ids.insert(id.clone()) {
            if let Some(bbox_element) = direct_child(element, "bbox") {
                nodes.push(Node {
                    id: id.clone(),
                    class_name: element.attributes.get("class").cloned().unwrap_or_default(),
                    bbox: parse_bbox(bbox_element)?,
                    orientation: element.attributes.get("orientation").cloned(),
                    parent_id: parent_glyph_id.clone(),
                });
            }
            for child in &element.children {
                if let XMLNode::Element(port) = child
                    && port.name == "port"
                    && let Some(port_id) = port.attributes.get("id")
                {
                    port_owners.insert(port_id.clone(), id.clone());
                }
            }
        }
    }
    for child in &element.children {
        if let XMLNode::Element(child) = child {
            collect_glyphs(child, child_parent_id.clone(), nodes, port_owners, seen_ids)?;
        }
    }
    Ok(())
}

fn collect_arcs(
    element: &Element,
    port_owners: &HashMap<String, String>,
    edges: &mut Vec<Edge>,
    seen_ids: &mut HashSet<String>,
) -> Result<()> {
    if element.name == "arc" {
        let id = element
            .attributes
            .get("id")
            .cloned()
            .ok_or_else(|| anyhow!("arc missing id"))?;
        ensure!(seen_ids.insert(id.clone()), "duplicate arc id {id}");
        let source = element
            .attributes
            .get("source")
            .cloned()
            .unwrap_or_default();
        let target = element
            .attributes
            .get("target")
            .cloned()
            .unwrap_or_default();
        let start_element =
            direct_child(element, "start").ok_or_else(|| anyhow!("arc {id} missing start"))?;
        let end_element =
            direct_child(element, "end").ok_or_else(|| anyhow!("arc {id} missing end"))?;
        let bends = element
            .children
            .iter()
            .filter_map(|child| match child {
                XMLNode::Element(child) if child.name == "next" => Some(parse_point(child)),
                _ => None,
            })
            .collect::<Result<Vec<_>>>()?;
        edges.push(Edge {
            id,
            class_name: element.attributes.get("class").cloned().unwrap_or_default(),
            source_node_id: port_owners
                .get(&source)
                .cloned()
                .or_else(|| (!source.is_empty()).then_some(source.clone())),
            target_node_id: port_owners
                .get(&target)
                .cloned()
                .or_else(|| (!target.is_empty()).then_some(target.clone())),
            source,
            target,
            start: parse_point(start_element)?,
            end: parse_point(end_element)?,
            bends,
        });
    }
    for child in &element.children {
        if let XMLNode::Element(child) = child {
            collect_arcs(child, port_owners, edges, seen_ids)?;
        }
    }
    Ok(())
}

fn format_coordinate(value: f64) -> String {
    let formatted = format!("{value:.6}");
    let trimmed = formatted.trim_end_matches('0').trim_end_matches('.');
    if trimmed == "-0" {
        "0".to_string()
    } else {
        trimmed.to_string()
    }
}

fn apply_edge_routes(root: &mut Element, routes: &EdgeRoutes) {
    if root.name == "arc"
        && let Some(id) = root.attributes.get("id")
        && let Some(route) = routes.get(id)
    {
        root.children
            .retain(|child| !matches!(child, XMLNode::Element(element) if element.name == "next"));
        let end_index = root
            .children
            .iter()
            .position(|child| matches!(child, XMLNode::Element(element) if element.name == "end"))
            .unwrap_or(root.children.len());
        let namespace = direct_child(root, "start").and_then(|start| start.namespace.clone());
        let prefix = direct_child(root, "start").and_then(|start| start.prefix.clone());
        for (offset, point) in route
            .iter()
            .skip(1)
            .take(route.len().saturating_sub(2))
            .enumerate()
        {
            let mut next = Element::new("next");
            next.namespace.clone_from(&namespace);
            next.prefix.clone_from(&prefix);
            next.attributes
                .insert("x".to_string(), format_coordinate(point.x));
            next.attributes
                .insert("y".to_string(), format_coordinate(point.y));
            root.children
                .insert(end_index + offset, XMLNode::Element(next));
        }
    }
    for child in &mut root.children {
        if let XMLNode::Element(child) = child {
            apply_edge_routes(child, routes);
        }
    }
}

fn snapshot_xml_geometry(root: &Element) -> BTreeMap<String, [String; 5]> {
    let mut snapshot = BTreeMap::new();
    collect_xml_geometry(root, &mut snapshot);
    snapshot
}

fn collect_xml_geometry(root: &Element, snapshot: &mut BTreeMap<String, [String; 5]>) {
    if root.name == "glyph"
        && let Some(id) = root.attributes.get("id")
        && let Some(bbox) = direct_child(root, "bbox")
    {
        snapshot.insert(
            id.clone(),
            [
                bbox.attributes.get("x").cloned().unwrap_or_default(),
                bbox.attributes.get("y").cloned().unwrap_or_default(),
                bbox.attributes.get("w").cloned().unwrap_or_default(),
                bbox.attributes.get("h").cloned().unwrap_or_default(),
                root.attributes
                    .get("orientation")
                    .cloned()
                    .unwrap_or_default(),
            ],
        );
    }
    for child in &root.children {
        if let XMLNode::Element(child) = child {
            collect_xml_geometry(child, snapshot);
        }
    }
}

fn semantic_fingerprint(root: &Element) -> Result<Vec<u8>> {
    let mut clone = root.clone();
    remove_arc_bends(&mut clone);
    let mut bytes = Vec::new();
    clone
        .write_with_config(&mut bytes, EmitterConfig::new().perform_indent(false))
        .context("failed to construct semantic fingerprint")?;
    Ok(bytes)
}

fn remove_arc_bends(root: &mut Element) {
    if root.name == "arc" {
        root.children
            .retain(|child| !matches!(child, XMLNode::Element(element) if element.name == "next"));
    }
    for child in &mut root.children {
        if let XMLNode::Element(child) = child {
            remove_arc_bends(child);
        }
    }
}

/// Count total routed interior bend points.
pub fn bend_count(routes: &EdgeRoutes) -> usize {
    routes
        .values()
        .map(|route| route.len().saturating_sub(2))
        .sum()
}

/// Return whether a route enters any unrelated obstacle plus clearance.
pub fn route_avoids_unrelated_nodes(
    route: &[Point],
    edge: &Edge,
    nodes: &[Node],
    clearance: f64,
) -> bool {
    first_intersected_unrelated_node(route, edge, nodes, clearance).is_none()
}

fn first_intersected_unrelated_node<'a>(
    route: &[Point],
    edge: &Edge,
    nodes: &'a [Node],
    clearance: f64,
) -> Option<&'a Node> {
    nodes
        .iter()
        .filter(|node| is_routing_obstacle(node))
        .filter(|node| !is_terminal_related_node(node, edge, nodes))
        .find(|node| {
            route.windows(2).any(|segment| {
                segment_enters_box(segment[0], segment[1], node.bbox.expanded(clearance))
            })
        })
}

fn is_terminal_related_node(node: &Node, edge: &Edge, nodes: &[Node]) -> bool {
    let terminal_ids = [
        edge.source_node_id.as_deref(),
        edge.target_node_id.as_deref(),
    ];
    let mut current = Some(node);
    while let Some(candidate) = current {
        if terminal_ids.contains(&Some(candidate.id.as_str())) {
            return true;
        }
        current = candidate
            .parent_id
            .as_deref()
            .and_then(|parent_id| nodes.iter().find(|parent| parent.id == parent_id));
    }
    false
}

#[cfg(test)]
mod tests {
    use std::io::Cursor;

    use pretty_assertions::assert_eq;

    use super::*;

    fn node(id: &str, x: f64, y: f64, width: f64, height: f64) -> Node {
        Node {
            id: id.to_string(),
            class_name: "macromolecule".to_string(),
            bbox: BoundingBox {
                x,
                y,
                width,
                height,
            },
            orientation: None,
            parent_id: None,
        }
    }

    fn edge(id: &str, start: Point, end: Point) -> Edge {
        Edge {
            id: id.to_string(),
            class_name: "production".to_string(),
            source: "source".to_string(),
            target: "target".to_string(),
            source_node_id: Some("source".to_string()),
            target_node_id: Some("target".to_string()),
            start,
            end,
            bends: Vec::new(),
        }
    }

    fn obstacle_graph(edges: Vec<Edge>) -> Graph {
        Graph {
            nodes: vec![
                node("source", 0.0, 40.0, 20.0, 20.0),
                node("obstacle", 80.0, 30.0, 40.0, 40.0),
                node("target", 180.0, 40.0, 20.0, 20.0),
            ],
            edges,
        }
    }

    #[test]
    fn routing_never_moves_nodes() {
        let graph = obstacle_graph(vec![edge(
            "edge",
            Point::new(20.0, 50.0),
            Point::new(180.0, 50.0),
        )]);
        let before = graph.nodes.clone();

        compute_edge_routes(&graph, &RoutingConfig::default()).expect("routing succeeds");

        assert_eq!(before, graph.nodes);
    }

    #[test]
    fn routes_around_unrelated_obstacle_with_clearance() {
        let graph = obstacle_graph(vec![edge(
            "edge",
            Point::new(20.0, 50.0),
            Point::new(180.0, 50.0),
        )]);
        let config = RoutingConfig::default();

        let routes = compute_edge_routes(&graph, &config).expect("routing succeeds");
        let route = routes.get("edge").expect("edge route exists");

        assert!(route.len() >= 4, "obstacle requires at least two bends");
        assert!(route_avoids_unrelated_nodes(
            route,
            &graph.edges[0],
            &graph.nodes,
            config.shape_buffer_distance,
        ));
    }

    #[test]
    fn returned_routes_are_orthogonal() {
        let graph = obstacle_graph(vec![edge(
            "edge",
            Point::new(20.0, 50.0),
            Point::new(180.0, 50.0),
        )]);

        let routes =
            compute_edge_routes(&graph, &RoutingConfig::default()).expect("routing succeeds");

        assert!(routes.values().all(|route| route_is_orthogonal(route)));
    }

    #[test]
    fn simplification_removes_duplicates_and_collinear_vertices() {
        let route = vec![
            Point::new(0.0, 0.0),
            Point::new(0.0, 0.0),
            Point::new(10.0, 0.0),
            Point::new(20.0, 0.0),
            Point::new(20.0, 10.0),
            Point::new(20.0, 20.0),
        ];

        assert_eq!(
            simplify_route(&route),
            vec![
                Point::new(0.0, 0.0),
                Point::new(20.0, 0.0),
                Point::new(20.0, 20.0),
            ]
        );
    }

    #[test]
    fn explicit_endpoints_remain_fixed() {
        let fixed_start = Point::new(20.0, 50.0);
        let fixed_end = Point::new(180.0, 50.0);
        let graph = obstacle_graph(vec![edge("edge", fixed_start, fixed_end)]);

        let routes =
            compute_edge_routes(&graph, &RoutingConfig::default()).expect("routing succeeds");
        let route = routes.get("edge").expect("edge route exists");

        assert_eq!(route.first(), Some(&fixed_start));
        assert_eq!(route.last(), Some(&fixed_end));
    }

    #[test]
    fn multiple_connectors_are_valid_without_node_changes() {
        let graph = obstacle_graph(vec![
            edge("first", Point::new(20.0, 47.0), Point::new(180.0, 47.0)),
            edge("second", Point::new(20.0, 53.0), Point::new(180.0, 53.0)),
        ]);
        let before = graph.nodes.clone();

        let routes =
            compute_edge_routes(&graph, &RoutingConfig::default()).expect("routing succeeds");

        assert_eq!(routes.len(), 2);
        assert!(routes.values().all(|route| route_is_orthogonal(route)));
        assert_eq!(before, graph.nodes);
    }

    #[test]
    fn sbgn_round_trip_changes_only_arc_bends() {
        let xml = r#"<?xml version="1.0" encoding="UTF-8"?>
<sbgn xmlns="http://sbgn.org/libsbgn/0.3">
  <map language="process description">
    <glyph id="source" class="macromolecule"><bbox x="0" y="40" w="20" h="20"/></glyph>
    <glyph id="obstacle" class="macromolecule"><bbox x="80" y="30" w="40" h="40"/></glyph>
    <glyph id="target" class="macromolecule"><bbox x="180" y="40" w="20" h="20"/></glyph>
    <arc id="edge" class="production" source="source" target="target">
      <start x="20" y="50"/><next x="60" y="50"/><end x="180" y="50"/>
    </arc>
  </map>
</sbgn>"#;
        let root = Element::parse(Cursor::new(xml)).expect("test XML parses");
        let graph = graph_from_xml(&root).expect("test graph parses");
        let mut document = SbgnDocument { root, graph };
        let geometry_before = snapshot_xml_geometry(&document.root);
        let semantics_before = semantic_fingerprint(&document.root).expect("fingerprint succeeds");

        let routes = document
            .route_arcs(&RoutingConfig::default())
            .expect("routing succeeds");

        assert_eq!(geometry_before, snapshot_xml_geometry(&document.root));
        assert_eq!(
            semantics_before,
            semantic_fingerprint(&document.root).expect("fingerprint succeeds")
        );
        let route = routes.get("edge").expect("edge route exists");
        assert_eq!(route.first(), Some(&Point::new(20.0, 50.0)));
        assert_eq!(route.last(), Some(&Point::new(180.0, 50.0)));
    }
}
