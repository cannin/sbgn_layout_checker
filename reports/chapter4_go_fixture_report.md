# SBGN layout checker report

Specification: SBGN Process Description Level 1 Version 2.1, Chapter 4.

Analyzed **44 SBGN files**: **43 requirement errors**, **22 recommendation warnings**.

| File | Glyphs | Arcs | Crossings | Arc-node crossings | Errors | Warnings |
|---|---:|---:|---:|---:|---:|---:|
| `testdata/chapter4/4_2_1_node_overlap_1.sbgn` | 4 | 3 | 0 | 1 | 1 | 1 |
| `testdata/chapter4/4_2_1_node_overlap_2.sbgn` | 4 | 3 | 0 | 1 | 1 | 1 |
| `testdata/chapter4/4_2_2_edge_z_order_1.sbgn` | 4 | 3 | 0 | 1 | 0 | 1 |
| `testdata/chapter4/4_2_2_edge_z_order_2.sbgn` | 4 | 3 | 0 | 1 | 0 | 1 |
| `testdata/chapter4/4_2_3_node_border_edge_overlap_1.sbgn` | 4 | 3 | 0 | 0 | 1 | 0 |
| `testdata/chapter4/4_2_3_node_border_edge_overlap_2.sbgn` | 4 | 3 | 0 | 0 | 1 | 0 |
| `testdata/chapter4/4_2_4_edge_overlap_1.sbgn` | 6 | 5 | 0 | 0 | 1 | 0 |
| `testdata/chapter4/4_2_4_edge_overlap_2.sbgn` | 6 | 5 | 0 | 0 | 1 | 0 |
| `testdata/chapter4/4_2_5_diagonal_orientation_1.sbgn` | 4 | 3 | 0 | 0 | 0 | 1 |
| `testdata/chapter4/4_2_5_diagonal_orientation_2.sbgn` | 4 | 3 | 0 | 0 | 0 | 1 |
| `testdata/chapter4/4_2_6_process_attachment_1.sbgn` | 4 | 3 | 0 | 0 | 2 | 0 |
| `testdata/chapter4/4_2_6_process_attachment_2.sbgn` | 4 | 3 | 0 | 0 | 2 | 0 |
| `testdata/chapter4/4_2_7_node_labels_1.sbgn` | 4 | 3 | 0 | 0 | 1 | 0 |
| `testdata/chapter4/4_2_7_node_labels_2.sbgn` | 4 | 3 | 0 | 0 | 1 | 0 |
| `testdata/chapter4/4_2_8_edge_labels_1.sbgn` | 4 | 3 | 0 | 0 | 2 | 0 |
| `testdata/chapter4/4_2_8_edge_labels_2.sbgn` | 4 | 3 | 0 | 0 | 2 | 0 |
| `testdata/chapter4/4_2_9_compartments_1.sbgn` | 5 | 3 | 0 | 2 | 8 | 2 |
| `testdata/chapter4/4_2_9_compartments_2.sbgn` | 5 | 3 | 0 | 2 | 8 | 2 |
| `testdata/chapter4/4_3_1_node_edge_crossing_1.sbgn` | 4 | 3 | 0 | 1 | 0 | 1 |
| `testdata/chapter4/4_3_1_node_edge_crossing_2.sbgn` | 4 | 3 | 0 | 1 | 0 | 1 |
| `testdata/chapter4/4_3_2_label_quality_1.sbgn` | 4 | 3 | 0 | 0 | 0 | 1 |
| `testdata/chapter4/4_3_2_label_quality_2.sbgn` | 4 | 3 | 0 | 0 | 0 | 1 |
| `testdata/chapter4/4_3_3_edge_crossings_1.sbgn` | 4 | 3 | 1 | 0 | 0 | 1 |
| `testdata/chapter4/4_3_3_edge_crossings_2.sbgn` | 4 | 3 | 1 | 0 | 0 | 1 |
| `testdata/chapter4/4_3_4_branch_proximity_1.sbgn` | 4 | 3 | 0 | 0 | 0 | 0 |
| `testdata/chapter4/4_3_4_branch_proximity_2.sbgn` | 4 | 3 | 0 | 0 | 0 | 0 |
| `testdata/chapter4/4_3_5_unit_information_1.sbgn` | 5 | 3 | 0 | 0 | 2 | 1 |
| `testdata/chapter4/4_3_5_unit_information_2.sbgn` | 5 | 3 | 0 | 0 | 2 | 1 |
| `testdata/chapter4/4_4_compactness_1.sbgn` | 4 | 3 | 0 | 0 | 0 | 0 |
| `testdata/chapter4/4_4_compactness_2.sbgn` | 4 | 3 | 0 | 0 | 0 | 0 |
| `testdata/chapter4/4_4_compartment_shading_1.sbgn` | 6 | 3 | 0 | 0 | 2 | 0 |
| `testdata/chapter4/4_4_compartment_shading_2.sbgn` | 6 | 3 | 0 | 0 | 3 | 0 |
| `testdata/chapter4/4_4_crossing_angle_1.sbgn` | 4 | 3 | 2 | 0 | 1 | 2 |
| `testdata/chapter4/4_4_crossing_angle_2.sbgn` | 4 | 3 | 2 | 0 | 1 | 2 |
| `testdata/chapter4/4_4_direction_1.sbgn` | 4 | 3 | 0 | 0 | 0 | 0 |
| `testdata/chapter4/4_4_direction_2.sbgn` | 4 | 3 | 0 | 0 | 0 | 0 |
| `testdata/chapter4/4_4_edge_bends_1.sbgn` | 4 | 3 | 0 | 0 | 0 | 0 |
| `testdata/chapter4/4_4_edge_bends_2.sbgn` | 4 | 3 | 0 | 0 | 0 | 0 |
| `testdata/chapter4/4_4_edge_length_1.sbgn` | 4 | 3 | 0 | 0 | 0 | 0 |
| `testdata/chapter4/4_4_edge_length_2.sbgn` | 4 | 3 | 0 | 0 | 0 | 0 |
| `testdata/chapter4/4_4_proximity_1.sbgn` | 4 | 3 | 0 | 0 | 0 | 0 |
| `testdata/chapter4/4_4_proximity_2.sbgn` | 4 | 3 | 0 | 0 | 0 | 0 |
| `testdata/chapter4/4_4_similarity_symmetry_1.sbgn` | 4 | 3 | 0 | 0 | 0 | 0 |
| `testdata/chapter4/4_4_similarity_symmetry_2.sbgn` | 4 | 3 | 0 | 0 | 0 | 0 |

## testdata/chapter4/4_2_1_node_overlap_1.sbgn

- **error 4.2.1** `node_overlap`: nodes "a" and "b" overlap or touch without an allowed containment relationship
- **warning 4.3.1** `node_edge_crossing`: arc "consume" crosses non-endpoint node "b"

## testdata/chapter4/4_2_1_node_overlap_2.sbgn

- **error 4.2.1** `node_overlap`: nodes "a" and "b" overlap or touch without an allowed containment relationship
- **warning 4.3.1** `node_edge_crossing`: arc "consume" crosses non-endpoint node "b"

## testdata/chapter4/4_2_2_edge_z_order_1.sbgn

- **warning 4.3.1** `node_edge_crossing`: arc "consume" crosses non-endpoint node "c"

## testdata/chapter4/4_2_2_edge_z_order_2.sbgn

- **warning 4.3.1** `node_edge_crossing`: arc "consume" crosses non-endpoint node "c"

## testdata/chapter4/4_2_3_node_border_edge_overlap_1.sbgn

- **error 4.2.3** `node_border_edge_overlap`: arc "consume" overlaps the border of node "c"

## testdata/chapter4/4_2_3_node_border_edge_overlap_2.sbgn

- **error 4.2.3** `node_border_edge_overlap`: arc "consume" overlaps the border of node "c"

## testdata/chapter4/4_2_4_edge_overlap_1.sbgn

- **error 4.2.4** `edge_edge_overlap_or_touch`: arcs "consume" and "consume_second" overlap or touch

## testdata/chapter4/4_2_4_edge_overlap_2.sbgn

- **error 4.2.4** `edge_edge_overlap_or_touch`: arcs "consume" and "consume_second" overlap or touch

## testdata/chapter4/4_2_5_diagonal_orientation_1.sbgn

- **warning 4.3.2** `node_label_not_fully_inside`: label for node "a" is not completely inside its node

## testdata/chapter4/4_2_5_diagonal_orientation_2.sbgn

- **warning 4.3.2** `node_label_not_fully_inside`: label for node "a" is not completely inside its node

## testdata/chapter4/4_2_6_process_attachment_1.sbgn

- **error 4.2.6** `process_flow_not_centered`: consumption arc "consume" is not centered on a side of process "p"
- **error 4.2.6** `process_flow_not_centered`: production arc "produce" is not centered on a side of process "p"

## testdata/chapter4/4_2_6_process_attachment_2.sbgn

- **error 4.2.6** `process_flow_not_centered`: consumption arc "consume" is not centered on a side of process "p"
- **error 4.2.6** `process_flow_not_centered`: production arc "produce" is not centered on a side of process "p"

## testdata/chapter4/4_2_7_node_labels_1.sbgn

- **error 4.2.7** `node_label_outside_node`: label for node "a" has no area inside its node

## testdata/chapter4/4_2_7_node_labels_2.sbgn

- **error 4.2.7** `node_label_outside_node`: label for node "a" has no area inside its node

## testdata/chapter4/4_2_8_edge_labels_1.sbgn

- **error 4.2.7** `label_label_overlap`: labels "a::label" and "consume_label::label" overlap or touch
- **error 4.2.8** `edge_label_overlaps_node`: edge label "consume_label::label" overlaps or touches node "a"

## testdata/chapter4/4_2_8_edge_labels_2.sbgn

- **error 4.2.7** `label_label_overlap`: labels "a::label" and "consume_label::label" overlap or touch
- **error 4.2.8** `edge_label_overlaps_node`: edge label "consume_label::label" overlaps or touches node "a"

## testdata/chapter4/4_2_9_compartments_1.sbgn

- **error 4.2.1** `node_overlap`: nodes "cell" and "c" overlap or touch without an allowed containment relationship
- **error 4.2.7** `node_label_overlaps_node`: label for node "a" overlaps or touches node "cell"
- **error 4.2.7** `node_label_overlaps_node`: label for node "b" overlaps or touches node "cell"
- **error 4.2.7** `node_label_overlaps_node`: label for node "c" overlaps or touches node "cell"
- **error 4.2.9** `process_arc_outside_compartment`: arc "consume" of process "p" leaves participant compartment "cell"
- **error 4.2.9** `process_arc_outside_compartment`: arc "produce" of process "p" leaves participant compartment "cell"
- **error 4.2.9** `process_arc_outside_compartment`: arc "stimulate" of process "p" leaves participant compartment "cell"
- **error 4.2.9** `process_outside_participant_compartment`: process "p" is not inside participant compartment "cell"
- **warning 4.3.1** `node_edge_crossing`: arc "consume" crosses non-endpoint node "b"
- **warning 4.3.1** `node_edge_crossing`: arc "stimulate" crosses non-endpoint node "b"

## testdata/chapter4/4_2_9_compartments_2.sbgn

- **error 4.2.1** `node_overlap`: nodes "cell" and "c" overlap or touch without an allowed containment relationship
- **error 4.2.7** `node_label_overlaps_node`: label for node "a" overlaps or touches node "cell"
- **error 4.2.7** `node_label_overlaps_node`: label for node "b" overlaps or touches node "cell"
- **error 4.2.7** `node_label_overlaps_node`: label for node "c" overlaps or touches node "cell"
- **error 4.2.9** `process_arc_outside_compartment`: arc "consume" of process "p" leaves participant compartment "cell"
- **error 4.2.9** `process_arc_outside_compartment`: arc "produce" of process "p" leaves participant compartment "cell"
- **error 4.2.9** `process_arc_outside_compartment`: arc "stimulate" of process "p" leaves participant compartment "cell"
- **error 4.2.9** `process_outside_participant_compartment`: process "p" is not inside participant compartment "cell"
- **warning 4.3.1** `node_edge_crossing`: arc "consume" crosses non-endpoint node "b"
- **warning 4.3.1** `node_edge_crossing`: arc "stimulate" crosses non-endpoint node "b"

## testdata/chapter4/4_3_1_node_edge_crossing_1.sbgn

- **warning 4.3.1** `node_edge_crossing`: arc "consume" crosses non-endpoint node "c"

## testdata/chapter4/4_3_1_node_edge_crossing_2.sbgn

- **warning 4.3.1** `node_edge_crossing`: arc "consume" crosses non-endpoint node "c"

## testdata/chapter4/4_3_2_label_quality_1.sbgn

- **warning 4.3.2** `node_label_not_fully_inside`: label for node "a" is not completely inside its node

## testdata/chapter4/4_3_2_label_quality_2.sbgn

- **warning 4.3.2** `node_label_not_fully_inside`: label for node "a" is not completely inside its node

## testdata/chapter4/4_3_3_edge_crossings_1.sbgn

- **warning 4.3.3** `edge_crossing`: arcs "consume" and "stimulate" cross

## testdata/chapter4/4_3_3_edge_crossings_2.sbgn

- **warning 4.3.3** `edge_crossing`: arcs "consume" and "stimulate" cross

## testdata/chapter4/4_3_5_unit_information_1.sbgn

- **error 4.2.1** `node_overlap`: nodes "a_info" and "b" overlap or touch without an allowed containment relationship
- **error 4.2.7** `node_label_overlaps_node`: label for node "b" overlaps or touches node "a_info"
- **warning 4.3.5** `unit_of_information_overlap`: unit of information "a_info" overlaps or touches element "b"

## testdata/chapter4/4_3_5_unit_information_2.sbgn

- **error 4.2.1** `node_overlap`: nodes "a_info" and "b" overlap or touch without an allowed containment relationship
- **error 4.2.7** `node_label_overlaps_node`: label for node "b" overlaps or touches node "a_info"
- **warning 4.3.5** `unit_of_information_overlap`: unit of information "a_info" overlaps or touches element "b"

## testdata/chapter4/4_4_compartment_shading_1.sbgn

- **error 4.2.7** `node_label_overlaps_node`: label for node "a" overlaps or touches node "left"
- **error 4.2.7** `node_label_overlaps_node`: label for node "b" overlaps or touches node "right"

## testdata/chapter4/4_4_compartment_shading_2.sbgn

- **error 4.2.1** `node_overlap`: nodes "right" and "c" overlap or touch without an allowed containment relationship
- **error 4.2.7** `node_label_overlaps_node`: label for node "a" overlaps or touches node "left"
- **error 4.2.7** `node_label_overlaps_node`: label for node "b" overlaps or touches node "right"

## testdata/chapter4/4_4_crossing_angle_1.sbgn

- **error 4.2.4** `edges_cross_more_than_once`: arcs "consume" and "stimulate" cross 2 times
- **warning 4.3.3** `edge_crossing`: arcs "consume" and "stimulate" cross
- **warning 4.3.3** `edge_crossing`: arcs "consume" and "stimulate" cross

## testdata/chapter4/4_4_crossing_angle_2.sbgn

- **error 4.2.4** `edges_cross_more_than_once`: arcs "consume" and "stimulate" cross 2 times
- **warning 4.3.3** `edge_crossing`: arcs "consume" and "stimulate" cross
- **warning 4.3.3** `edge_crossing`: arcs "consume" and "stimulate" cross

## Coverage notes

See [`docs/chapter4_rules.md`](../docs/chapter4_rules.md) for exact coverage, assumptions, and underspecified rules.

Reproduce with `go run ./go/cmd/sbgn_layout_checker --format markdown --output reports/chapter4_go_fixture_report.md testdata/chapter4`.
