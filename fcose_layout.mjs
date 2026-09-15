#!/usr/bin/env node

import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";
import seedrandom from "seedrandom";

cytoscape.use(fcose);

function readStandardInput() {
  return new Promise((resolve, reject) => {
    let input = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      input += chunk;
    });
    process.stdin.on("end", () => resolve(input));
    process.stdin.on("error", reject);
  });
}

const payload = JSON.parse(await readStandardInput());
const elements = [
  ...payload.nodes.map((node) => ({
    group: "nodes",
    data: {
      id: node.id,
      parent: node.parent ?? undefined,
      width: node.width,
      height: node.height,
    },
    position: { x: node.x, y: node.y },
  })),
  ...payload.edges.map((edge) => ({
    group: "edges",
    data: {
      id: edge.id,
      source: edge.source,
      target: edge.target,
    },
  })),
];

function runLayout(seed) {
  const graph = cytoscape({
    headless: true,
    styleEnabled: true,
    elements,
    style: [
      {
        selector: "node",
        style: {
          width: "data(width)",
          height: "data(height)",
          shape: "rectangle",
          padding: 0,
        },
      },
      {
        selector: ":parent",
        style: {
          padding: 30,
        },
      },
    ],
  });

  const originalRandom = Math.random;
  Math.random = seedrandom(String(seed));
  try {
    graph
      .layout({
        name: "fcose",
        quality: "proof",
        randomize: true,
        animate: false,
        fit: false,
      })
      .run();
  } finally {
    Math.random = originalRandom;
  }

  const nodes = graph.nodes().map((node) => {
    const position = node.position();
    return {
      id: node.id(),
      x: position.x,
      y: position.y,
      width: node.width(),
      height: node.height(),
    };
  });
  graph.destroy();
  return { seed, nodes };
}

const isBatch = Array.isArray(payload.seeds);
const seeds = isBatch ? payload.seeds : [payload.seed];
const runs = seeds.map((seed) => runLayout(seed));
const output = isBatch ? { runs } : { nodes: runs[0].nodes };
process.stdout.write(`${JSON.stringify(output)}\n`, () => process.exit(0));
