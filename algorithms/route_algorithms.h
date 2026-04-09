#ifndef ROUTE_ALGORITHMS_H
#define ROUTE_ALGORITHMS_H

#include <stddef.h>

#define MAX_VERTICES 64
#define MAX_PATH_LENGTH 64
#define INF_COST 1e18

typedef enum {
    MODE_CAR = 0,
    MODE_BIKE = 1,
    MODE_WALK = 2
} TravelMode;

typedef struct {
    int exists;
    double distance_km;
    double speed_kmph[3];
    int incident_count;
    int severity_score;
    double crowd_density;
    double unsafe_zone_penalty;
} Edge;

typedef struct {
    int vertex_count;
    Edge edges[MAX_VERTICES][MAX_VERTICES];
} Graph;

typedef struct {
    double incident_weight;
    double severity_weight;
    double crowd_weight;
    double unsafe_zone_weight;
    double distance_weight;
    double time_weight;
    double mode_risk_multiplier[3];
} SafetyWeights;

typedef struct {
    int found;
    int node_count;
    int nodes[MAX_PATH_LENGTH];
    double total_distance_km;
    double total_time_minutes;
    double total_cost;
    double total_safety_penalty;
} PathResult;

void graph_init(Graph *graph, int vertex_count);
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
);

SafetyWeights default_safety_weights(void);
const char *travel_mode_name(TravelMode mode);

int shortest_path_dijkstra(
    const Graph *graph,
    int start,
    int destination,
    TravelMode mode,
    PathResult *result
);

int safest_path_dijkstra(
    const Graph *graph,
    int start,
    int destination,
    TravelMode mode,
    const SafetyWeights *weights,
    PathResult *result
);

#endif
