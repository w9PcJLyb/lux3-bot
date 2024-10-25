from libcpp cimport bool, string
from libcpp.pair cimport pair
from libcpp.vector cimport vector


cdef extern from "src/core.cpp":
    pass


cdef extern from "src/include/core.h":

    cdef cppclass AbsGraph:
        AbsGraph() except +
        size_t size()
        double calculate_cost(vector[int])
        bool is_valid_path(vector[int])
        void reverse_inplace()
        vector[pair[int, double]] get_neighbors(int)
        vector[vector[int]] find_components()
        vector[vector[int]] find_scc()
        bool adjacent(int, int)
        void set_pause_action_cost(double)
        double get_pause_action_cost()
        void set_edge_collision(bool)
        bool edge_collision()

    cdef cppclass AbsGrid(AbsGraph):
        bool has_obstacle(int)
        void add_obstacle(int)
        void remove_obstacle(int)
        void clear_weights()
        void set_weights(vector[double]&) except +
        void update_weight(int, double) except +
        double get_weight(int) except +
        vector[double] get_weights()
        int get_pause_action_cost_type()
        void set_pause_action_cost_type(int) except +

    cdef cppclass AbsPathFinder:
        AbsPathFinder() except +
        vector[int] find_path(int, int)

    cdef cppclass AbsMAPF:
        AbsMAPF() except +
        vector[vector[int]] mapf(vector[int], vector[int])


cdef extern from "src/reservation_table.cpp":
    pass


cdef extern from "src/include/reservation_table.h":
    cdef cppclass ReservationTable:
        ReservationTable(int) except +
        bool is_reserved(int, int)
        void add_path(int, vector[int], bool, bool)
        void add_vertex_constraint(int, int)
        void add_edge_constraint(int, int, int)
        void add_additional_weight(int, int, double)
        void add_weight_path(int, vector[int], double)
        double get_additional_weight(int, int)
        int last_time_reserved(int)


cdef extern from "src/graph.cpp":
    pass


cdef extern from "src/include/graph.h":

    cdef cppclass Graph(AbsGraph):
        Graph(int, bool) except +
        Graph(int, bool, vector[vector[double]]) except +
        void add_edges(vector[int], vector[int], vector[double])
        size_t num_edges()
        vector[vector[double]] get_edges()
        vector[vector[double]] get_coordinates()
        void set_coordinates(vector[vector[double]])
        bool has_coordinates()
        double estimate_distance(int v1, int v2)
        Graph* create_reversed_graph()


cdef extern from "src/grid.cpp":
    pass


cdef extern from "src/include/grid.h":

    cdef cppclass Grid(AbsGrid):
        bool passable_left_right_border, passable_up_down_border
        double diagonal_movement_cost_multiplier

        Grid(int, int) except +
        Grid(int, int, vector[double]) except +
        unsigned int get_diagonal_movement()
        void set_diagonal_movement(int)


cdef extern from "src/bfs.cpp":
    pass


cdef extern from "src/include/bfs.h":

    cdef cppclass BFS(AbsPathFinder):
        BFS(AbsGraph*) except +
        vector[int] find_path(int, int)


cdef extern from "src/dijkstra.cpp":
    pass


cdef extern from "src/include/dijkstra.h":

    cdef cppclass Dijkstra(AbsPathFinder):
        Dijkstra(AbsGraph*) except +
        vector[int] find_path(int, int)


cdef extern from "src/a_star.cpp":
    pass


cdef extern from "src/include/a_star.h":

    cdef cppclass AStar(AbsPathFinder):
        AStar(AbsGraph*) except +
        vector[int] find_path(int, int)


cdef extern from "src/resumable_search.cpp":
    pass


cdef extern from "src/include/resumable_search.h":

    cdef cppclass ResumableBFS:
        ResumableBFS(AbsGraph*, int) except +
        double distance(int)
        vector[int] find_path(int)
        int start_node()
        void set_start_node(int)

    cdef cppclass ResumableDijkstra:
        ResumableDijkstra(AbsGraph*, int) except +
        double distance(int)
        vector[int] find_path(int)
        int start_node()
        void set_start_node(int)


cdef extern from "src/space_time_a_star.cpp":
    pass


cdef extern from "src/include/space_time_a_star.h":

    cdef cppclass SpaceTimeAStar(AbsPathFinder):
        SpaceTimeAStar(AbsGraph*) except +
        vector[int] find_path_with_depth_limit(int, int, int, ReservationTable*)
        vector[int] find_path_with_exact_length(int, int, int, ReservationTable*)
        vector[int] find_path_with_length_limit(int, int, int, ReservationTable*)
