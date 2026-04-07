#include "route_algorithms.h"

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

SafetyWeights default_safety_weights(void) {
    SafetyWeights weights;

    weights.incident_weight = 4.0;
    weights.severity_weight = 5.0;
    weights.crowd_weight = 3.0;
    weights.unsafe_zone_weight = 8.0;
    weights.distance_weight = 0.6;
    weights.time_weight = 0.8;
    weights.mode_risk_multiplier[MODE_CAR] = 0.95;
    weights.mode_risk_multiplier[MODE_BIKE] = 1.10;
    weights.mode_risk_multiplier[MODE_WALK] = 1.25;

    return weights;
}

static void reset_result(PathResult *result) {
    if (!result) {
        return;
    }
    memset(result, 0, sizeof(*result));
}

static double safety_penalty_for_edge(
    const Edge *edge,
    TravelMode mode,
    const SafetyWeights *weights
) {
    double base_penalty;
    double mode_multiplier;

    base_penalty =
        (edge->incident_count * weights->incident_weight) +
        (edge->severity_score * weights->severity_weight) +
        (edge->crowd_density * weights->crowd_weight) +
        (edge->unsafe_zone_penalty * weights->unsafe_zone_weight);

    mode_multiplier = weights->mode_risk_multiplier[mode];
    return base_penalty * mode_multiplier;
}

static double safest_cost_for_edge(
    const Edge *edge,
    TravelMode mode,
    const SafetyWeights *weights
) {
    double time_minutes = edge_time_minutes(edge, mode);
    double safety_penalty = safety_penalty_for_edge(edge, mode, weights);

    return
        (edge->distance_km * weights->distance_weight) +
        (time_minutes * weights->time_weight) +
        safety_penalty;
}

static void build_path_result(
    const Graph *graph,
    const int previous[],
    int start,
    int destination,
    TravelMode mode,
    const SafetyWeights *weights,
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
        result->total_safety_penalty += safety_penalty_for_edge(edge, mode, weights);
    }
}

int safest_path_dijkstra(
    const Graph *graph,
    int start,
    int destination,
    TravelMode mode,
    const SafetyWeights *weights,
    PathResult *result
) {
    double cost[MAX_VERTICES];
    int previous[MAX_VERTICES];
    int visited[MAX_VERTICES];
    SafetyWeights active_weights;

    if (!valid_vertex(graph, start) || !valid_vertex(graph, destination) || !result) {
        return 0;
    }

    active_weights = weights ? *weights : default_safety_weights();

    for (int i = 0; i < graph->vertex_count; ++i) {
        cost[i] = INF_COST;
        previous[i] = -1;
        visited[i] = 0;
    }
    cost[start] = 0.0;

    for (int step = 0; step < graph->vertex_count; ++step) {
        double best_cost = INF_COST;
        int current = -1;

        for (int i = 0; i < graph->vertex_count; ++i) {
            if (!visited[i] && cost[i] < best_cost) {
                best_cost = cost[i];
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

            edge_cost = safest_cost_for_edge(edge, mode, &active_weights);
            candidate_cost = cost[current] + edge_cost;

            if (candidate_cost < cost[next]) {
                cost[next] = candidate_cost;
                previous[next] = current;
            }
        }
    }

    if (cost[destination] >= INF_COST / 2.0) {
        reset_result(result);
        return 0;
    }

    build_path_result(graph, previous, start, destination, mode, &active_weights, cost[destination], result);
    return result->found;
}
