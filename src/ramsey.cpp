#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using Clock = std::chrono::steady_clock;
using Clique = std::vector<int>;
struct LimitReached {};

struct Counters {
    uint64_t candidates = 0, edge_checks = 0, prefixes = 0, intersections = 0;
};

// One clock poll per 4096 search operations keeps time limits cooperative
// without putting a clock call in every edge comparison.
struct Budget {
    Clock::time_point deadline;
    uint64_t operations = 0;
    void poll() const { if (Clock::now() >= deadline) throw LimitReached{}; }
    void tick() { if ((++operations & 4095U) == 0) poll(); }
};

struct Graph {
    int n;
    std::array<std::array<uint8_t, 64>, 64> edge{};
    std::array<std::array<uint64_t, 64>, 2> neighbours{};
    explicit Graph(int size) : n(size) {}
    void set(int u, int v, int c) {
        edge[u][v] = edge[v][u] = static_cast<uint8_t>(c);
        for (int colour = 0; colour < 2; ++colour) {
            neighbours[colour][u] &= ~(uint64_t{1} << v);
            neighbours[colour][v] &= ~(uint64_t{1} << u);
        }
        neighbours[c][u] |= uint64_t{1} << v;
        neighbours[c][v] |= uint64_t{1} << u;
    }
    void randomize(std::mt19937_64& rng) {
        for (int u = 0; u < n; ++u)
            for (int v = u + 1; v < n; ++v) set(u, v, int(rng() & 1U));
    }
    std::string bits() const {
        std::string out;
        for (int u = 0; u < n; ++u)
            for (int v = u + 1; v < n; ++v) out += char('0' + edge[u][v]);
        return out;
    }
};

uint64_t after(int v) {
    // Shifting by 64 is undefined; this branch also supports vertex 63.
    return v == 63 ? 0 : (~uint64_t{0} << (v + 1));
}

bool naive(const Graph& g, int k, Clique& answer, Counters& c, Budget& budget) {
    Clique s(k);
    for (int i = 0; i < k; ++i) s[i] = i;
    while (true) {
        budget.tick();
        ++c.candidates;
        const int colour = g.edge[s[0]][s[1]];
        ++c.edge_checks;
        bool mono = true;
        for (int i = 0; i < k && mono; ++i)
            for (int j = i + 1; j < k; ++j) {
                if (i == 0 && j == 1) continue;
                ++c.edge_checks;
                if (g.edge[s[i]][s[j]] != colour) { mono = false; break; }
            }
        if (mono) { answer = s; return true; }
        int i = k - 1;
        while (i >= 0 && s[i] == g.n - k + i) --i;
        if (i < 0) return false;
        ++s[i];
        for (int j = i + 1; j < k; ++j) s[j] = s[j - 1] + 1;
    }
}

bool scalar_extend(const Graph& g, int k, int colour, Clique& s,
                   Clique& answer, Counters& c, Budget& budget) {
    ++c.prefixes;
    budget.tick();
    if (int(s.size()) == k) { answer = s; return true; }
    const int last = g.n - (k - int(s.size()));
    for (int v = s.back() + 1; v <= last; ++v) {
        budget.tick();
        ++c.candidates;
        bool valid = true;
        for (int u : s) {
            ++c.edge_checks;
            if (g.edge[u][v] != colour) { valid = false; break; }
        }
        if (valid) {
            s.push_back(v);
            if (scalar_extend(g, k, colour, s, answer, c, budget)) return true;
            s.pop_back();
        }
    }
    return false;
}

bool bitset_extend(const Graph& g, int k, int colour, Clique& s, uint64_t options,
                   Clique& answer, Counters& c, Budget& budget) {
    ++c.prefixes;
    budget.tick();
    if (int(s.size()) == k) { answer = s; return true; }
    const int need = k - int(s.size());
    if (__builtin_popcountll(options) < need) return false;
    while (options) {
        if (__builtin_popcountll(options) < need) break;
        budget.tick();
        ++c.candidates;
        const int v = __builtin_ctzll(options);
        options &= options - 1;
        ++c.intersections;
        const uint64_t next = options & g.neighbours[colour][v];
        s.push_back(v);
        if (bitset_extend(g, k, colour, s, next, answer, c, budget)) return true;
        s.pop_back();
    }
    return false;
}

bool find_bad(const Graph& g, int k, const std::string& method,
              Clique& answer, Counters& c, Budget& budget) {
    budget.poll();
    if (method == "naive") return naive(g, k, answer, c, budget);
    for (int u = 0; u <= g.n - k; ++u) {
        for (int v = u + 1; v <= g.n - k + 1; ++v) {
            budget.tick();
            ++c.candidates;
            ++c.edge_checks;
            Clique s{u, v};
            const int colour = g.edge[u][v];
            if (method == "branching") {
                if (scalar_extend(g, k, colour, s, answer, c, budget)) return true;
            } else {
                ++c.intersections;
                const uint64_t options = g.neighbours[colour][u] &
                                         g.neighbours[colour][v] & after(v);
                if (bitset_extend(g, k, colour, s, options, answer, c, budget)) return true;
            }
        }
    }
    return false;
}

struct Args {
    int n = 0, k = 0;
    uint64_t seed = 0, max_resamplings = 100000;
    double seconds = 5;
    std::string method = "hs_bitset", bits;
    bool search_only = false;
};

uint64_t integer(const std::string& s) {
    if (s.empty() || s[0] == '-') throw std::invalid_argument("expected a nonnegative integer");
    size_t used = 0;
    const auto value = std::stoull(s, &used);
    if (used != s.size()) throw std::invalid_argument("invalid integer: " + s);
    return value;
}

Args parse(int argc, char** argv) {
    Args a;
    for (int i = 1; i < argc; ++i) {
        const std::string key = argv[i];
        if (key == "--search-only") { a.search_only = true; continue; }
        if (i + 1 == argc) throw std::invalid_argument("missing value for " + key);
        const std::string value = argv[++i];
        if (key == "--n" || key == "--k") {
            const auto number = integer(value);
            if (number > 64) throw std::invalid_argument("n and k must be at most 64");
            (key == "--n" ? a.n : a.k) = int(number);
        } else if (key == "--seed") a.seed = integer(value);
        else if (key == "--max-resamplings") a.max_resamplings = integer(value);
        else if (key == "--seconds") {
            size_t used = 0;
            a.seconds = std::stod(value, &used);
            if (used != value.size() || !std::isfinite(a.seconds))
                throw std::invalid_argument("invalid time limit");
        } else if (key == "--method") a.method = value;
        else if (key == "--bits") a.bits = value;
        else throw std::invalid_argument("unknown argument: " + key);
    }
    if (a.n < 2 || a.k < 2 || a.k > a.n || a.seconds <= 0 || a.seconds > 86400)
        throw std::invalid_argument("require 2 <= k <= n <= 64 and 0 < seconds <= 86400");
    if (a.method != "naive" && a.method != "branching" && a.method != "hs_bitset")
        throw std::invalid_argument("method must be naive, branching, or hs_bitset");
    if (!a.bits.empty() && (a.bits.size() != size_t(a.n * (a.n - 1) / 2) ||
        a.bits.find_first_not_of("01") != std::string::npos))
        throw std::invalid_argument("bits must encode the upper triangle in row order");
    return a;
}

double elapsed(Clock::time_point start) {
    return std::chrono::duration<double>(Clock::now() - start).count();
}

int main(int argc, char** argv) {
    try {
        const Args a = parse(argc, argv);
        const auto start = Clock::now();
        Budget budget{start + std::chrono::duration_cast<Clock::duration>(
            std::chrono::duration<double>(a.seconds))};
        std::mt19937_64 rng(a.seed);
        Graph graph(a.n);
        graph.randomize(rng);
        if (!a.bits.empty()) {
            size_t i = 0;
            for (int u = 0; u < a.n; ++u)
                for (int v = u + 1; v < a.n; ++v) graph.set(u, v, a.bits[i++] - '0');
        }
        const std::string initial_bits = graph.bits();
        const double initialization_seconds = elapsed(start);
        Counters c;
        uint64_t repairs = 0, calls = 0, trajectory_hash = 14695981039346656037ULL;
        double search_seconds = 0, resampling_seconds = 0;
        std::string status;
        Clique answer;
        while (true) {
            answer.clear();
            ++calls;
            const auto search_start = Clock::now();
            bool found = false;
            try {
                found = find_bad(graph, a.k, a.method, answer, c, budget);
                search_seconds += elapsed(search_start);
            } catch (const LimitReached&) {
                search_seconds += elapsed(search_start);
                status = "timeout";
                break;
            }
            if (a.search_only) { status = found ? "found" : "absent"; break; }
            if (!found) { status = "success"; break; }
            if (repairs == a.max_resamplings) { status = "resampling_limit"; break; }
            const auto repair_start = Clock::now();
            for (int u : answer) { trajectory_hash ^= uint64_t(u + 1); trajectory_hash *= 1099511628211ULL; }
            for (size_t i = 0; i < answer.size(); ++i)
                for (size_t j = i + 1; j < answer.size(); ++j)
                    graph.set(answer[i], answer[j], int(rng() & 1U));
            ++repairs;
            resampling_seconds += elapsed(repair_start);
        }
        const double total_seconds = elapsed(start);
        std::ostringstream hash;
        hash << std::hex << std::setfill('0') << std::setw(16) << trajectory_hash;
        std::cout << std::setprecision(12)
          << "{\"n\":" << a.n << ",\"k\":" << a.k << ",\"seed\":" << a.seed
          << ",\"method\":\"" << a.method << "\",\"status\":\"" << status
          << "\",\"resamplings\":" << repairs << ",\"search_calls\":" << calls
          << ",\"candidates_tested\":" << c.candidates << ",\"edge_checks\":" << c.edge_checks
          << ",\"prefixes\":" << c.prefixes << ",\"bitset_intersections\":" << c.intersections
          << ",\"initialization_seconds\":" << initialization_seconds
          << ",\"search_seconds\":" << search_seconds
          << ",\"resampling_seconds\":" << resampling_seconds
          << ",\"total_seconds\":" << total_seconds
          << ",\"trajectory_hash\":\"" << hash.str()
          << "\",\"initial_edge_bits\":\"" << initial_bits
          << "\",\"final_edge_bits\":\"" << graph.bits() << "\",\"clique\":[";
        for (size_t i = 0; i < answer.size(); ++i) std::cout << (i ? "," : "") << answer[i];
        std::cout << "]}\n";
        return 0; // Capped runs are data; argument/implementation failures are errors.
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 2;
    }
}
