#include "route_algorithms.h"

#include <stdio.h>

static void print_result(const char *title, const PathResult *result) {
    printf("%s\n", title);
    if (!result->found) {
        printf("  No path found.\n\n");
        return;
    }

    printf("  Path: ");
    for (int i = 0; i < result->node_count; ++i) {
        printf("%d", result->nodes[i]);
        if (i + 1 < result->node_count) {
            printf(" -> ");
        }
    }
    printf("\n");
    printf("  Distance: %.2f km\n", result->total_distance_km);
    printf("  Time: %.2f min\n", result->total_time_minutes);
    printf("  Combined cost: %.2f\n", result->total_cost);
    printf("  Safety penalty: %.2f\n\n", result->total_safety_penalty);
}

int main(void) {
    Graph graph;
    PathResult shortest;
    PathResult safest;
    SafetyWeights weights = default_safety_weights();

    graph_init(&graph, 6);

    graph_add_edge(&graph, 0, 1, 2.0, 32.0, 18.0, 5.0, 1, 1, 1.0, 0.0, 1);
    graph_add_edge(&graph, 1, 2, 1.5, 30.0, 16.0, 5.0, 0, 0, 1.5, 0.0, 1);
    graph_add_edge(&graph, 0, 3, 2.2, 28.0, 15.0, 4.5, 2, 4, 2.5, 1.5, 1);
    graph_add_edge(&graph, 3, 4, 1.4, 30.0, 18.0, 5.0, 0, 1, 1.0, 0.0, 1);
    graph_add_edge(&graph, 4, 2, 1.1, 35.0, 18.0, 5.2, 0, 0, 0.5, 0.0, 1);
    graph_add_edge(&graph, 1, 4, 2.4, 27.0, 14.0, 4.7, 3, 5, 3.5, 2.0, 1);
    graph_add_edge(&graph, 2, 5, 1.8, 34.0, 17.0, 5.0, 1, 2, 1.0, 0.0, 1);
    graph_add_edge(&graph, 4, 5, 2.0, 31.0, 16.0, 4.8, 0, 0, 0.8, 0.0, 1);

    shortest_path_dijkstra(&graph, 0, 5, MODE_CAR, &shortest);
    safest_path_dijkstra(&graph, 0, 5, MODE_CAR, &weights, &safest);

    printf("Travel mode: %s\n\n", travel_mode_name(MODE_CAR));
    print_result("Shortest Path (Dijkstra)", &shortest);
    print_result("Safest Path (Modified Weighted Dijkstra)", &safest);

    return 0;
}
