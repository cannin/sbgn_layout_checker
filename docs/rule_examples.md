# Implemented rule examples

Each image below is generated from a semantically valid SBGN-PD fixture by
`scripts/render_rule_examples.py`. The red annotation names the Chapter 4 rule
and highlights the elements or exact point reported by the Go checker.

| Rule | Demonstrated finding | Annotated PNG |
|---|---|---|
| 4.2.1 | Nodes overlap or touch without allowed containment. | ![Rule 4.2.1 node overlap](images/rules/rule_4_2_1.png) |
| 4.2.3 | An edge overlaps a node border. | ![Rule 4.2.3 node-border edge overlap](images/rules/rule_4_2_3.png) |
| 4.2.4 | Two edges overlap or touch. | ![Rule 4.2.4 edge overlap](images/rules/rule_4_2_4.png) |
| 4.2.5 | A node declares a non-axis-aligned orientation. | ![Rule 4.2.5 node orientation](images/rules/rule_4_2_5.png) |
| 4.2.6 | A process flow arc is not centered on a process side. | ![Rule 4.2.6 process attachment](images/rules/rule_4_2_6.png) |
| 4.2.7 | A node label lies outside its node. | ![Rule 4.2.7 node label](images/rules/rule_4_2_7.png) |
| 4.2.8 | An edge label overlaps a node. | ![Rule 4.2.8 edge label](images/rules/rule_4_2_8.png) |
| 4.2.9 | A process lies outside its participants' compartment. | ![Rule 4.2.9 compartment placement](images/rules/rule_4_2_9.png) |
| 4.3.1 | An edge crosses a non-endpoint node. | ![Rule 4.3.1 node-edge crossing](images/rules/rule_4_3_1.png) |
| 4.3.2 | A label is not fully contained by its node. | ![Rule 4.3.2 label quality](images/rules/rule_4_3_2.png) |
| 4.3.3 | Two edges cross. | ![Rule 4.3.3 edge crossing](images/rules/rule_4_3_3.png) |
| 4.3.5 | A unit-of-information glyph overlaps another element. | ![Rule 4.3.5 unit of information](images/rules/rule_4_3_5.png) |

The remaining documented guidelines are metric-only or require visual
information that cannot be derived portably from SBGN-ML, so they do not claim
checker findings and are intentionally excluded from this gallery.