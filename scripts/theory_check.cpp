// This executable uses a temporary copy of the solver with a per-level counter.
// Its entry point performs count and certificate checks without emitting timings.
#define main ramsey_benchmark_main
#include "ramsey_instrumented.cpp"
#undef main

namespace {

Graph from_bits(int n, const std::string& bits) {
    if (bits.size() != size_t(n * (n - 1) / 2) ||
        bits.find_first_not_of("01") != std::string::npos) {
        throw std::invalid_argument("invalid graph certificate");
    }
    Graph graph(n);
    size_t index = 0;
    for (int u = 0; u < n; ++u) {
        for (int v = u + 1; v < n; ++v) {
            graph.set(u, v, bits[index++] - '0');
        }
    }
    return graph;
}

uint64_t count_extensions(const Graph& graph, int colour, uint64_t candidates,
                          int remaining) {
    if (remaining == 0) return 1;
    uint64_t count = 0;
    while (__builtin_popcountll(candidates) >= remaining) {
        const int v = __builtin_ctzll(candidates);
        candidates &= candidates - 1;
        count += count_extensions(graph, colour, candidates & graph.neighbours[colour][v],
                                  remaining - 1);
    }
    return count;
}

uint64_t count_bitset(const Graph& graph, int k) {
    uint64_t count = 0;
    for (int u = 0; u < graph.n; ++u) {
        for (int v = u + 1; v < graph.n; ++v) {
            const int colour = graph.edge[u][v];
            const auto candidates = graph.neighbours[colour][u] &
                                    graph.neighbours[colour][v] & after(v);
            count += count_extensions(graph, colour, candidates, k - 2);
        }
    }
    return count;
}

uint64_t count_naive(const Graph& graph, int k) {
    Clique vertices(k);
    for (int i = 0; i < k; ++i) vertices[i] = i;
    uint64_t count = 0;
    while (true) {
        const int colour = graph.edge[vertices[0]][vertices[1]];
        bool monochromatic = true;
        for (int i = 0; i < k && monochromatic; ++i) {
            for (int j = i + 1; j < k; ++j) {
                if (graph.edge[vertices[i]][vertices[j]] != colour) {
                    monochromatic = false;
                    break;
                }
            }
        }
        if (monochromatic) ++count;

        int i = k - 1;
        while (i >= 0 && vertices[i] == graph.n - k + i) --i;
        if (i < 0) return count;
        ++vertices[i];
        for (int j = i + 1; j < k; ++j) vertices[j] = vertices[j - 1] + 1;
    }
}

void replay(int n, int k, uint64_t seed, uint64_t repair_limit) {
    std::mt19937_64 rng(seed);
    Graph graph(n);
    graph.randomize(rng);
    const auto initial = graph.bits();
    Budget budget{Clock::time_point::max()};
    Counters counters;
    Clique answer;
    uint64_t repairs = 0;
    uint64_t trajectory_hash = 14695981039346656037ULL;
    while (find_bad(graph, k, "hs_bitset", answer, counters, budget)) {
        if (repairs == repair_limit) throw std::runtime_error("replay reached repair limit");
        for (const int u : answer) {
            trajectory_hash ^= uint64_t(u + 1);
            trajectory_hash *= 1099511628211ULL;
        }
        for (size_t i = 0; i < answer.size(); ++i) {
            for (size_t j = i + 1; j < answer.size(); ++j) {
                graph.set(answer[i], answer[j], int(rng() & 1U));
            }
        }
        ++repairs;
    }
    std::ostringstream hash;
    hash << std::hex << std::setfill('0') << std::setw(16) << trajectory_hash;
    std::cout << repairs << ' ' << hash.str() << ' ' << initial << ' ' << graph.bits() << '\n';
}

void visit(const Graph& graph, int k) {
    Budget budget{Clock::time_point::max()};
    Counters counters;
    Clique answer;
    if (find_bad(graph, k, "hs_bitset", answer, counters, budget)) {
        throw std::runtime_error("final graph contains a monochromatic target clique");
    }
    std::cout << counters.prefixes;
    for (int i = 1; i <= k; ++i) std::cout << ' ' << counters.visited_by_size[i];
    std::cout << '\n';
}

} // namespace

int main() {
    try {
        std::string operation;
        while (std::cin >> operation) {
            int n = 0, k = 0;
            std::string input;
            if (!(std::cin >> n >> k >> input) || k < 2 || k > n || n > 64) {
                throw std::invalid_argument("expected operation, n, k and seed or graph bits");
            }
            if (operation == "replay") {
                uint64_t repair_limit = 0;
                if (!(std::cin >> repair_limit)) throw std::invalid_argument("missing repair limit");
                replay(n, k, integer(input), repair_limit);
                continue;
            }
            const auto graph = from_bits(n, input);
            if (operation == "count_bitset") std::cout << count_bitset(graph, k) << '\n';
            else if (operation == "count_naive") std::cout << count_naive(graph, k) << '\n';
            else if (operation == "visit") visit(graph, k);
            else throw std::invalid_argument("unknown check operation");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
