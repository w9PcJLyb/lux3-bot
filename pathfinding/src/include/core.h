#pragma once

#include <cmath>
#include <queue>
#include <vector>
#include <random>
#include <numeric>
#include <ostream>
#include <cassert>
#include <iostream>
#include <algorithm>
#include <stdexcept>

using std::cout;
using std::endl;
using std::pair;
using std::vector;
using std::priority_queue;

typedef vector<int> Path;


class AbsGraph {
    public:
        AbsGraph() {};
        virtual ~AbsGraph() {};
        virtual size_t size() const = 0;
        virtual vector<pair<int, double>> get_neighbors(int node, bool reversed=false) = 0;
        virtual bool has_coordinates() const = 0;

        // returns a lower bound of the distance between two vertices
        // used by A* algorithm
        virtual double estimate_distance(int v1, int v2) const = 0;

        virtual bool is_directed_graph() const = 0;

        virtual double calculate_cost(Path& path);
        bool is_valid_path(Path& path);

        // returns connected components in an undirected graph
        virtual vector<vector<int>> find_components();

        // returns Strongly Connected Components (SCC) in a directed graph
        virtual vector<vector<int>> find_scc();

        // returns true if there is a path of length 1 from vertex v1 to vertex v2
        virtual bool adjacent(int v1, int v2);

        virtual std::string node_to_string(int v) const;
        void print_path(Path& path) const;

        double min_weight() const {
            return min_weight_;
        }

    protected:
        // the minimum value in weights, used in the heuristic function (estimate_distance)
        double min_weight_ = 1.0;

    private:
        vector<int> find_component_(vector<bool> &visited, int start);

    // For multi agent path finding
    protected:
        // the cost of the pause action
        double pause_action_cost_ = 1;

        // if edge_collision_ is true, two agents can not pass on the same edge
        // at the same time in two different directions
        bool edge_collision_ = false;

    public:
        void set_pause_action_cost(double cost) {
            if (cost < 0)
                throw std::invalid_argument("Pause action cost must be non-negative");
            pause_action_cost_ = cost;
        }

        virtual double get_pause_action_cost() const {
            return pause_action_cost_;
        }

        virtual double get_pause_action_cost(int v) const {
            return pause_action_cost_;
        }

        virtual void set_edge_collision(bool b) {
            edge_collision_ = b;
        }

        bool edge_collision() const {
            return edge_collision_;
        }
};


class AbsGrid : public AbsGraph {

    public:
        size_t size() const {
            return weights_.size();
        }

        bool has_coordinates() const {
            return true;
        }

        bool is_directed_graph() const {
            return false;
        }

        double get_weight(int node) const {
            return weights_.at(node);
        }

        vector<double> get_weights() const {
            return weights_;
        }

        bool has_obstacle(int node) const {
            return get_weight(node) == -1;
        }

        void add_obstacle(int node) {
            update_weight(node, -1);
        }

        void remove_obstacle(int node) {
            update_weight(node, 1);
        }

        void clear_weights() {
            std::fill(weights_.begin(), weights_.end(), 1);
        }

        void update_weight(int node, double w);
        void set_weights(vector<double> &weights);
        vector<vector<int>> find_components() override;

        int get_pause_action_cost_type() {
            return pause_action_cost_type_;
        }

        void set_pause_action_cost_type(int type) {
            if (type < 0 || type > 1) {
                throw std::invalid_argument("value must be uint and les than 2");
            }
            pause_action_cost_type_ = type;
        }

        double get_pause_action_cost() const {
            return pause_action_cost_;
        }

        double get_pause_action_cost(int v) const {
            if (pause_action_cost_type_ == 0)
                return pause_action_cost_;
            else {
                double w = weights_[v];
                if (w < 0)
                    return 0;
                return w;
            }
        }

    protected:
        // if weight == -1 - there is an impassable obstacle, the node is unreachable
        // if weight >= 0 - weight is the cost of entering this node
        vector<double> weights_;

        // 0 - pause action cost is the same for all nodes and is equal to graph.pause_action_cost_
        // 1 - pause action cost is equal to the weight of the node
        int pause_action_cost_type_ = 0;
};


class AbsPathFinder {
    public:
        AbsPathFinder() {};
        virtual ~AbsPathFinder() {};
        virtual Path find_path(int start, int end) = 0;
};


class AbsMAPF {
    public:
        AbsMAPF() {};
        virtual ~AbsMAPF() {};
        virtual vector<Path> mapf(vector<int> starts, vector<int> goals) = 0;
};


class timeout_exception : public std::runtime_error {
    public:
        using std::runtime_error::runtime_error;
};


void ensure_path_length(Path& path, int length);
