#include "route_algorithms.h"

#include <stdio.h>
#include <string.h>

static double default_speed_for_mode(TravelMode mode) {
    switch (mode) {
        case MODE_CAR: return 32.0;
        case MODE_BIKE: return 18.0;
        case MODE_WALK: return 5.0;
        default: return 20.0;
    }
}

static double edge_speed(const Edge *edge, TravelMode mode) {
    double speed = edge->speed_kmph[mode];
    return speed > 0.0 ? speed : default_speed_for_mode(mode);
}

static double edge_time_minutes(const Edge *edge, TravelMode mode) {
    double speed = edge_speed(edge, mode);
    if (speed <= 0.0) {
        return INF_COST;
    }
    return (edge->distance_km / speed) * 60.0;
}

static int valid_vertex(const Graph *graph, int vertex) {
    return graph && vertex >= 0 && vertex < graph->vertex_count;
}

void graph_init(Graph *graph, int vertex_count) {
    if (!graph) {
        return;
    }
    if (vertex_count < 0) {
        vertex_count = 0;
    }
    if (vertex_count > MAX_VERTICES) {
        vertex_count = MAX_VERTICES;
    }
    graph->vertex_count = vertex_count;
    memset(graph->edges, 0, sizeof(graph->edges));
}

void graph_add_edge(
    Graph *graph,
    int from,
    int to,
    double distance_km,
    double car_speed_kmph,
    double bike_speed_kmph,
    double walk_speed_kmph,
    int incident_count,
    int severity_score,
    double crowd_density,
    double unsafe_zone_penalty,
    int bidirectional
) {
    Edge edge;

    if (!valid_vertex(graph, from) || !valid_vertex(graph, to)) {
        return;
    }

    edge.exists = 1;
    edge.distance_km = distance_km;
    edge.speed_kmph[MODE_CAR] = car_speed_kmph;
    edge.speed_kmph[MODE_BIKE] = bike_speed_kmph;
    edge.speed_kmph[MODE_WALK] = walk_speed_kmph;
    edge.incident_count = incident_count;
    edge.severity_score = severity_score;
    edge.crowd_density = crowd_density;
    edge.unsafe_zone_penalty = unsafe_zone_penalty;

    graph->edges[from][to] = edge;
    if (bidirectional) {
        graph->edges[to][from] = edge;
    }
}

const char *travel_mode_name(TravelMode mode) {
    switch (mode) {
        case MODE_CAR: return "car";
        case MODE_BIKE: return "bike";
        case MODE_WALK: return "walk";
        default: return "unknown";
    }
}

static void reset_result(PathResult *result) {
    if (!result) {
        return;
    }
    memset(result, 0, sizeof(*result));
}

static void build_path_result(
    const Graph *graph,
    const int previous[],
    int start,
    int destination,
    TravelMode mode,
    double final_cost,
    PathResult *result
) {
    int reverse_nodes[MAX_PATH_LENGTH];
    int count = 0;
    int current = destination;

    reset_result(result);
    result->total_cost = final_cost;

    while (current != -1 && count < MAX_PATH_LENGTH) {
        reverse_nodes[count++] = current;
        if (current == start) {
            break;
        }
        current = previous[current];
    }

    if (count == 0 || reverse_nodes[count - 1] != start) {
        return;
    }

    result->found = 1;
    result->node_count = count;

    for (int i = 0; i < count; ++i) {
        result->nodes[i] = reverse_nodes[count - 1 - i];
    }

    for (int i = 0; i < count - 1; ++i) {
        const Edge *edge = &graph->edges[result->nodes[i]][result->nodes[i + 1]];
        result->total_distance_km += edge->distance_km;
        result->total_time_minutes += edge_time_minutes(edge, mode);
    }
}

int shortest_path_dijkstra(
    const Graph *graph,
    int start,
    int destination,
    TravelMode mode,
    PathResult *result
) {
    double distance[MAX_VERTICES];
    int previous[MAX_VERTICES];
    int visited[MAX_VERTICES];

    if (!valid_vertex(graph, start) || !valid_vertex(graph, destination) || !result) {
        return 0;
    }

    for (int i = 0; i < graph->vertex_count; ++i) {
        distance[i] = INF_COST;
        previous[i] = -1;
        visited[i] = 0;
    }
    distance[start] = 0.0;

    for (int step = 0; step < graph->vertex_count; ++step) {
        double best_cost = INF_COST;
        int current = -1;

        for (int i = 0; i < graph->vertex_count; ++i) {
            if (!visited[i] && distance[i] < best_cost) {
                best_cost = distance[i];
                current = i;
            }
        }

        if (current == -1) {
            break;
        }
        if (current == destination) {
            break;
        }

        visited[current] = 1;

        for (int next = 0; next < graph->vertex_count; ++next) {
            const Edge *edge = &graph->edges[current][next];
            double edge_cost;
            double candidate_cost;

            if (!edge->exists || visited[next]) {
                continue;
            }

            edge_cost = edge_time_minutes(edge, mode);
            candidate_cost = distance[current] + edge_cost;

            if (candidate_cost < distance[next]) {
                distance[next] = candidate_cost;
                previous[next] = current;
            }
        }
    }

    if (distance[destination] >= INF_COST / 2.0) {
        reset_result(result);
        return 0;
    }

    build_path_result(graph, previous, start, destination, mode, distance[destination], result);
    return result->found;
}
