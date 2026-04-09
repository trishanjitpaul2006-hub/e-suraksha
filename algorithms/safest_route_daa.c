#include <float.h>
#include <stdio.h>
#include <string.h>

#define MAX_NODES 20
#define NO_EDGE 0

typedef enum {
    MODE_CAR = 0,
    MODE_BIKE = 1,
    MODE_WALK = 2
} TravelMode;

typedef struct {
    int exists;
    double distance;
    int incidents;
    int severity;
    double unsafe_penalty;
    double crowd_score;
    double speed_kmph;
} Edge;

typedef struct {
    int found;
    int path[MAX_NODES];
    int path_length;
    double total_distance;
    double total_eta_minutes;
    double total_safe_cost;
    int total_incidents;
    int total_severity;
    double total_unsafe_penalty;
    double total_crowd_score;
    double total_mode_risk;
} SafePathResult;

static double get_mode_risk(TravelMode mode) {
    switch (mode) {
        case MODE_WALK: return 3.0;
        case MODE_BIKE: return 2.0;
        case MODE_CAR: return 1.0;
        default: return 1.0;
    }
}

static const char *mode_name(TravelMode mode) {
    switch (mode) {
        case MODE_WALK: return "walk";
        case MODE_BIKE: return "bike";
        case MODE_CAR: return "car";
        default: return "car";
    }
}

/*
 * Mandatory DAA safe-cost formula:
 * SafeCost = 0.5*D + 4*I + 3*S + 5*U + 2*M - 2*C
 *
 * Lower SafeCost means safer edge/path.
 * Crowd reduces risk, so the final term is negative.
 */
double calculateSafeCost(Edge e, int mode) {
    double mode_risk = get_mode_risk((TravelMode) mode);
    return
        (0.5 * e.distance) +
        (4.0 * e.incidents) +
        (3.0 * e.severity) +
        (5.0 * e.unsafe_penalty) +
        (2.0 * mode_risk) -
        (2.0 * e.crowd_score);
}

static double edge_eta_minutes(const Edge *edge) {
    if (!edge || edge->speed_kmph <= 0.0) {
        return 0.0;
    }
    return (edge->distance / edge->speed_kmph) * 60.0;
}

static void init_graph(Edge graph[MAX_NODES][MAX_NODES], int node_count) {
    int i;
    int j;
    for (i = 0; i < node_count; i++) {
        for (j = 0; j < node_count; j++) {
            graph[i][j].exists = NO_EDGE;
        }
    }
}

static void add_edge(
    Edge graph[MAX_NODES][MAX_NODES],
    int from,
    int to,
    double distance,
    int incidents,
    int severity,
    double unsafe_penalty,
    double crowd_score,
    double speed_kmph,
    int bidirectional
) {
    graph[from][to].exists = 1;
    graph[from][to].distance = distance;
    graph[from][to].incidents = incidents;
    graph[from][to].severity = severity;
    graph[from][to].unsafe_penalty = unsafe_penalty;
    graph[from][to].crowd_score = crowd_score;
    graph[from][to].speed_kmph = speed_kmph;

    if (bidirectional) {
        graph[to][from] = graph[from][to];
    }
}

static SafePathResult modified_dijkstra_safest_path(
    Edge graph[MAX_NODES][MAX_NODES],
    int node_count,
    int start,
    int destination,
    TravelMode mode
) {
    double dist[MAX_NODES];
    int visited[MAX_NODES];
    int previous[MAX_NODES];
    SafePathResult result;
    int i;

    memset(&result, 0, sizeof(result));

    for (i = 0; i < node_count; i++) {
        dist[i] = DBL_MAX;
        visited[i] = 0;
        previous[i] = -1;
    }

    dist[start] = 0.0;

    for (i = 0; i < node_count; i++) {
        int current = -1;
        double best = DBL_MAX;
        int j;

        for (j = 0; j < node_count; j++) {
            if (!visited[j] && dist[j] < best) {
                best = dist[j];
                current = j;
            }
        }

        if (current == -1) {
            break;
        }

        visited[current] = 1;
        if (current == destination) {
            break;
        }

        for (j = 0; j < node_count; j++) {
            if (!graph[current][j].exists || visited[j]) {
                continue;
            }

            double edge_cost = calculateSafeCost(graph[current][j], mode);
            double candidate = dist[current] + edge_cost;

            if (candidate < dist[j]) {
                dist[j] = candidate;
                previous[j] = current;
            }
        }
    }

    if (dist[destination] == DBL_MAX) {
        return result;
    }

    {
        int reverse_path[MAX_NODES];
        int count = 0;
        int current = destination;

        while (current != -1) {
            reverse_path[count++] = current;
            current = previous[current];
        }

        result.found = 1;
        result.path_length = count;
        result.total_safe_cost = dist[destination];

        for (i = 0; i < count; i++) {
            result.path[i] = reverse_path[count - i - 1];
        }

        for (i = 0; i < count - 1; i++) {
            Edge edge = graph[result.path[i]][result.path[i + 1]];
            result.total_distance += edge.distance;
            result.total_eta_minutes += edge_eta_minutes(&edge);
            result.total_incidents += edge.incidents;
            result.total_severity += edge.severity;
            result.total_unsafe_penalty += edge.unsafe_penalty;
            result.total_crowd_score += edge.crowd_score;
            result.total_mode_risk += get_mode_risk(mode);
        }
    }

    return result;
}

static void print_result(const SafePathResult *result, TravelMode mode) {
    int i;
    if (!result->found) {
      printf("No safest path found.\n");
      return;
    }

    printf("Safest path for mode: %s\n", mode_name(mode));
    printf("Path: ");
    for (i = 0; i < result->path_length; i++) {
        printf("%d", result->path[i]);
        if (i + 1 < result->path_length) {
            printf(" -> ");
        }
    }
    printf("\n");
    printf("Distance: %.2f km\n", result->total_distance);
    printf("ETA: %.2f min\n", result->total_eta_minutes);
    printf("Incidents: %d\n", result->total_incidents);
    printf("Severity: %d\n", result->total_severity);
    printf("Unsafe zone penalty: %.2f\n", result->total_unsafe_penalty);
    printf("Crowd score: %.2f\n", result->total_crowd_score);
    printf("Mode risk total: %.2f\n", result->total_mode_risk);
    printf("Total SafeCost: %.2f\n", result->total_safe_cost);
    printf("Formula used: 0.5*D + 4*I + 3*S + 5*U + 2*M - 2*C\n");
}

int main(void) {
    Edge graph[MAX_NODES][MAX_NODES];
    SafePathResult result;
    int node_count = 6;

    init_graph(graph, node_count);

    /*
     * Crowd scoring rule:
     * low crowd = 0.5 (unsafe)
     * medium crowd = 2.5 (safest)
     * high crowd = 1.5 (still supportive, but slightly less safe than medium)
     */
    add_edge(graph, 0, 1, 3.0, 1, 2, 0.6, 2.5, 24.0, 1);
    add_edge(graph, 1, 5, 3.5, 0, 1, 0.3, 1.5, 26.0, 1);
    add_edge(graph, 0, 2, 2.2, 2, 4, 1.4, 0.5, 22.0, 1);
    add_edge(graph, 2, 3, 1.8, 1, 3, 1.0, 0.5, 18.0, 1);
    add_edge(graph, 3, 5, 2.1, 1, 2, 0.7, 1.5, 20.0, 1);
    add_edge(graph, 1, 4, 2.8, 0, 1, 0.2, 2.5, 21.0, 1);
    add_edge(graph, 4, 5, 2.2, 0, 1, 0.4, 2.5, 19.0, 1);

    result = modified_dijkstra_safest_path(graph, node_count, 0, 5, MODE_WALK);
    print_result(&result, MODE_WALK);

    return 0;
}
