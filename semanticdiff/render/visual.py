"""Interactive visual delta graph export for semanticdiff.

Converts RDF delta triples into an interactive Vis.js network graph HTML page,
showing added, deleted, and updated nodes and edges with distinct colors.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import graph_diff, to_isomorphic
from rdflib.term import Node

_COLOR_ADDED = "#22c55e"  # green
_COLOR_DELETED = "#ef4444"  # red
_COLOR_UPDATED = "#f59e0b"  # amber / orange
_COLOR_FONT = "#f8fafc"  # white

_STATUS_ADDED = "added"
_STATUS_DELETED = "deleted"
_STATUS_UPDATED = "updated"

_URI_TYPE = "uri"
_LITERAL_TYPE = "literal"
_BNODE_TYPE = "bnode"

_ATTR_COLOR = "color"
_ATTR_STATUS = "status"

_PREFIX_MAP: dict[str, str] = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf:",
    "http://www.w3.org/2000/01/rdf-schema#": "rdfs:",
    "http://www.w3.org/2002/07/owl#": "owl:",
    "http://www.w3.org/2004/02/skos/core#": "skos:",
    "http://xmlns.com/foaf/0.1/": "foaf:",
    "http://purl.org/dc/elements/1.1/": "dc:",
    "http://purl.org/dc/terms/": "dcterms:",
    "http://schema.org/": "schema:",
}

VALID_STATUSES = {"added", "deleted", "updated"}


def render_diff_html(
    base: Graph,
    later: Graph,
    output_path: Path,
    title: str = "Semantic RDF Difference",
    *,
    status: str | None = None,
) -> Path:
    """Generate interactive Vis.js HTML visualization for graph diff."""
    if output_path.exists():
        return output_path

    nodes, edges = build_delta_data(base, later, status=status)
    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)

    html_content = (
        _HTML_TEMPLATE.replace("__TITLE__", title)
        .replace("__NODES_JSON__", nodes_json)
        .replace("__EDGES_JSON__", edges_json)
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")
    return output_path


def build_delta_data(
    base: Graph, later: Graph, status: str | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    `status` optionally filters elements: 'added', 'deleted', or 'updated'. If None, we take all
    """
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(f"Unknown status '{status}'; expected one of {sorted(VALID_STATUSES)}")

    # Ignore in_both which is the first returned value _
    _, only_base, only_later = graph_diff(to_isomorphic(base), to_isomorphic(later))

    # Pre-build edge lists and gather node sets in a single pass per graph
    added_edges, added_nodes = _extract_edges_and_nodes(only_later, added=True)
    deleted_edges, deleted_nodes = _extract_edges_and_nodes(only_base, added=False)

    all_nodes = sorted(added_nodes | deleted_nodes, key=str)

    # When status is Null, we take all affeced edges, and nodes
    if status is None:
        edges = added_edges + deleted_edges
        nodes = [
            _get_node_dict(node=n, in_added=n in added_nodes, in_deleted=n in deleted_nodes)
            for n in all_nodes
        ]
    # Filter edges based on requested status
    elif status == "added":
        edges = added_edges
        nodes = _get_affected_nodes_from_edges(edges, added_nodes, deleted_nodes, all_nodes)
    elif status == "deleted":
        edges = deleted_edges
        nodes = _get_affected_nodes_from_edges(edges, added_nodes, deleted_nodes, all_nodes)
    # Status Updated means intersection of added Node and deleted Nodes
    elif status == "updated":
        updated_node_ids = {str(n) for n in (added_nodes & deleted_nodes)}
        # Edges added only if either from Node or to Node is implied in updated_nodes
        edges = [
            edge
            for edge in (added_edges + deleted_edges)
            if edge["from"] in updated_node_ids or edge["to"] in updated_node_ids
        ]
        nodes = _get_affected_nodes_from_edges(edges, added_nodes, deleted_nodes, all_nodes)

    return nodes, edges


def _get_affected_nodes_from_edges(edges, added_nodes, deleted_nodes, all_nodes):
    edge_implied_node_ids = {e["from"] for e in edges} | {e["to"] for e in edges}
    return [
        _get_node_dict(node=node, in_added=node in added_nodes, in_deleted=node in deleted_nodes)
        for node in all_nodes
        if str(node) in edge_implied_node_ids
    ]


def _extract_edges_and_nodes(triples, added: bool):
    edges = []
    nodes = set()
    for s, p, o in triples:
        edges.append(_edge_dict(s, p, o, added=added))
        nodes.add(s)
        nodes.add(o)
    return edges, nodes


def _shorten_uri(uri_str: str) -> str:
    """Convert URI into CURIE if standard prefix matches, else return local name."""
    for prefix_uri, prefix_alias in _PREFIX_MAP.items():
        if uri_str.startswith(prefix_uri):
            return prefix_alias + uri_str[len(prefix_uri) :]
    if "#" in uri_str:
        return uri_str.split("#")[-1]
    if "/" in uri_str:
        return uri_str.split("/")[-1]
    return uri_str


def _format_node_label(node: Node) -> str:
    """Format an RDF node into a readable label."""
    if isinstance(node, URIRef):
        return _shorten_uri(str(node))
    if isinstance(node, Literal):
        val = str(node)
        if len(val) > 30:
            val = f"{val[:27]}..."
        if node.language:
            return f'"{val}"@{node.language}'
        if node.datatype:
            return f'"{val}"^^<{_shorten_uri(str(node.datatype))}>'
        return f'"{val}"'
    if isinstance(node, BNode):
        return f"_:{node}"
    return str(node)


def _get_node_dict(node: Node, in_added: bool, in_deleted: bool) -> dict[str, Any]:
    if in_added and in_deleted:
        status = _STATUS_UPDATED
        color = _COLOR_UPDATED
    elif in_added:
        status = _STATUS_ADDED
        color = _COLOR_ADDED
    else:
        status = _STATUS_DELETED
        color = _COLOR_DELETED

    is_uri = isinstance(node, URIRef)
    node_type = (
        _URI_TYPE if is_uri else (_LITERAL_TYPE if isinstance(node, Literal) else _BNODE_TYPE)
    )
    label = _format_node_label(node)
    node_id = str(node)

    return {
        "id": node_id,
        "label": label,
        "title": f"{node_id} [{status.upper()}]",
        "full_name": node_id,
        "type": node_type,
        _ATTR_STATUS: status,
        _ATTR_COLOR: color,
        "shape": "dot" if is_uri else "ellipse",
        "size": 18 if is_uri else 12,
        "font": {_ATTR_COLOR: _COLOR_FONT},
    }


def _edge_dict(s: Node, p: Node, o: Node, added: bool) -> dict[str, Any]:
    status = _STATUS_ADDED if added else _STATUS_DELETED
    color = _COLOR_ADDED if added else _COLOR_DELETED
    title_status = "ADDED (+)" if added else "DELETED (-)"
    pred_str = str(p)

    return {
        "from": str(s),
        "to": str(o),
        "label": _shorten_uri(pred_str),
        "title": f"Predicate: {pred_str}\nStatus: {title_status}",
        _ATTR_STATUS: status,
        _ATTR_COLOR: color,
        "arrows": "to",
        "width": 2,
    }


_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <script>
function neighbourhoodHighlight(params) {
  allNodes = nodes.get({ returnType: "Object" });
  if (params.nodes.length > 0) {
    highlightActive = true;
    var i, j;
    var selectedNode = params.nodes[0];
    var degrees = 2;

    for (let nodeId in allNodes) {
      allNodes[nodeId].color = "rgba(200,200,200,0.5)";
      if (allNodes[nodeId].hiddenLabel === undefined) {
        allNodes[nodeId].hiddenLabel = allNodes[nodeId].label;
        allNodes[nodeId].label = undefined;
      }
    }
    var connectedNodes = network.getConnectedNodes(selectedNode);
    var allConnectedNodes = [];

    for (i = 1; i < degrees; i++) {
      for (j = 0; j < connectedNodes.length; j++) {
        allConnectedNodes = allConnectedNodes.concat(
          network.getConnectedNodes(connectedNodes[j])
        );
      }
    }

    for (i = 0; i < allConnectedNodes.length; i++) {
      allNodes[allConnectedNodes[i]].color = "rgba(150,150,150,0.75)";
      if (allNodes[allConnectedNodes[i]].hiddenLabel !== undefined) {
        allNodes[allConnectedNodes[i]].label =
          allNodes[allConnectedNodes[i]].hiddenLabel;
        allNodes[allConnectedNodes[i]].hiddenLabel = undefined;
      }
    }

    for (i = 0; i < connectedNodes.length; i++) {
      allNodes[connectedNodes[i]].color = nodeColors[connectedNodes[i]];
      if (allNodes[connectedNodes[i]].hiddenLabel !== undefined) {
        allNodes[connectedNodes[i]].label =
          allNodes[connectedNodes[i]].hiddenLabel;
        allNodes[connectedNodes[i]].hiddenLabel = undefined;
      }
    }

    allNodes[selectedNode].color = nodeColors[selectedNode];
    if (allNodes[selectedNode].hiddenLabel !== undefined) {
      allNodes[selectedNode].label = allNodes[selectedNode].hiddenLabel;
      allNodes[selectedNode].hiddenLabel = undefined;
    }
  } else if (highlightActive === true) {
    for (let nodeId in allNodes) {
      allNodes[nodeId].color = nodeColors[nodeId];
      if (allNodes[nodeId].hiddenLabel !== undefined) {
        allNodes[nodeId].label = allNodes[nodeId].hiddenLabel;
        allNodes[nodeId].hiddenLabel = undefined;
      }
    }
    highlightActive = false;
  }

  var updateArray = [];
  if (params.nodes.length > 0) {
    for (let nodeId in allNodes) {
      if (allNodes.hasOwnProperty(nodeId)) {
        updateArray.push(allNodes[nodeId]);
      }
    }
    nodes.update(updateArray);
  } else {
    for (let nodeId in allNodes) {
      if (allNodes.hasOwnProperty(nodeId)) {
        updateArray.push(allNodes[nodeId]);
      }
    }
    nodes.update(updateArray);
  }
}

function filterHighlight(params) {
  allNodes = nodes.get({ returnType: "Object" });
  if (params.nodes.length > 0) {
    filterActive = true;
    let selectedNodes = params.nodes;

    for (let nodeId in allNodes) {
      allNodes[nodeId].hidden = true;
      if (allNodes[nodeId].savedLabel === undefined) {
        allNodes[nodeId].savedLabel = allNodes[nodeId].label;
        allNodes[nodeId].label = undefined;
      }
    }

    for (let i=0; i < selectedNodes.length; i++) {
      allNodes[selectedNodes[i]].hidden = false;
      if (allNodes[selectedNodes[i]].savedLabel !== undefined) {
        allNodes[selectedNodes[i]].label = allNodes[selectedNodes[i]].savedLabel;
        allNodes[selectedNodes[i]].savedLabel = undefined;
      }
    }
  } else if (filterActive === true) {
    for (let nodeId in allNodes) {
      allNodes[nodeId].hidden = false;
      if (allNodes[nodeId].savedLabel !== undefined) {
        allNodes[nodeId].label = allNodes[nodeId].savedLabel;
        allNodes[nodeId].savedLabel = undefined;
      }
    }
    filterActive = false;
  }

  var updateArray = [];
  if (params.nodes.length > 0) {
    for (let nodeId in allNodes) {
      if (allNodes.hasOwnProperty(nodeId)) {
        updateArray.push(allNodes[nodeId]);
      }
    }
    nodes.update(updateArray);
  } else {
    for (let nodeId in allNodes) {
      if (allNodes.hasOwnProperty(nodeId)) {
        updateArray.push(allNodes[nodeId]);
      }
    }
    nodes.update(updateArray);
  }
}
        </script>
        <link
          rel="stylesheet"
          href="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/dist/vis-network.min.css"
          integrity="sha512-WgxfT5LWjfszlPHXRmBWHkV2eceiWTOBvrKCNbdgDYTHrT2AeLCGbF4sZlZw3UMN3WtL0tGUoIAKsu8mllg/XA=="
          crossorigin="anonymous"
          referrerpolicy="no-referrer"
        />
        <script
          src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js"
          integrity="sha512-LnvoEWDFrqGHlHmDD2101OrLcbsfkrzoSpvtSQtxK3RMnRV0eOkhhBN2dXHKRrUU8p2DGRTk35n4O8nWSVe1mQ=="
          crossorigin="anonymous"
          referrerpolicy="no-referrer"
        ></script>
        <link
          href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/css/bootstrap.min.css"
          rel="stylesheet"
          integrity="sha384-eOJMYsd53ii+scO/bJGFsiCZc+5NDVN2yr8+0RDqr0Ql0h+rP48ckxlpbzKgwra6"
          crossorigin="anonymous"
        />
        <center>
          <h1 style="color: #f8fafc; margin-top: 10px;">__TITLE__</h1>
        </center>
        <style type="text/css">
             body {
                 background-color: #0f172a;
                 color: #f8fafc;
                 margin: 0;
             }
             #mynetwork {
                 width: 100%;
                 height: calc(100vh - 60px);
                 background-color: #0f172a;
                 position: relative;
             }
        </style>
    </head>
    <body>
        <div id="mynetwork"></div>
        <script type="text/javascript">
              var edges, nodes, allNodes, allEdges, nodeColors, network, container, options, data;
              var highlightActive = false;
              var filterActive = false;

              function drawGraph() {
                  container = document.getElementById('mynetwork');
                  nodes = new vis.DataSet(__NODES_JSON__);
                  edges = new vis.DataSet(__EDGES_JSON__);

                  nodeColors = {};
                  allNodes = nodes.get({ returnType: "Object" });
                  for (let nodeId in allNodes) {
                    nodeColors[nodeId] = allNodes[nodeId].color;
                  }
                  allEdges = edges.get({ returnType: "Object" });
                  data = {nodes: nodes, edges: edges};

                  options = {
                    configure: { enabled: false },
                    edges: {
                        color: { inherit: false },
                        smooth: { enabled: true, type: "dynamic" }
                    },
                    interaction: {
                        dragNodes: true,
                        hideEdgesOnDrag: false,
                        hideNodesOnDrag: false
                    },
                    physics: {
                        enabled: true,
                        stabilization: {
                            enabled: true,
                            fit: true,
                            iterations: 1000,
                            onlyDynamicEdges: false,
                            updateInterval: 50
                        }
                    }
                  };

                  network = new vis.Network(container, data, options);
                  return network;
              }
              drawGraph();
        </script>
    </body>
</html>
"""
