#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <deque>
#include <set>
#include <string>
#include <queue>
#include <vector>

using namespace std;

typedef int32_t i32;
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;


extern "C" {
    typedef struct {
        u16 posx;
        u16 posy;
        u8 rotation; // r * 90
        u32 grid_size; // len(tuples)
        u16* grid;
    } Problem;

    u32 solve(Problem* problem, u32 ans_size, char* ans);
}


#define PACK_POS(x, y) ((u32(y) << 16) + u32(x))
#define POSX(p) ((p) & 0xffff)
#define POSY(p) (((p) >> 16) & 0xffff)


static vector<u32>
move_bot(const vector<u32>& bot, i32 tx, i32 ty) {
    vector<u32> res;
    res.reserve(bot.size());
    for (auto p : bot) {
        i32 px = POSX(p);
        i32 py = POSY(p);
        u32 q = PACK_POS(px + tx, py + ty);
        res.emplace_back(q);
    }
    return res;
}


static vector<u32>
rotate_bot(const vector<u32>& bot, u8 rotation) {
    // origin at bot[0]
    vector<u32> res;
    res.reserve(bot.size());

    u32 origin = bot[0];
    i32 ox = POSX(origin);
    i32 oy = POSY(origin);

    for (auto p : bot) {
        i32 px = POSX(p);
        i32 py = POSY(p);
        i32 tx = px - ox;
        i32 ty = py - oy;
        for (u8 i = 0; i < rotation % 4; i++) {
            i32 t = tx;
            tx = -ty;
            ty = tx;
        }
        u32 q = PACK_POS(ox + tx, oy + ty);
        res.emplace_back(q);
    }

    return res;
}


typedef enum {
    ActionMoveUp,
    ActionMoveRight,
    ActionMoveDown,
    ActionMoveLeft,
    ActionPass,
    ActionRotateCW,
    ActionRotateCCW,
    ActionUseWheels,
    ActionUseDrill,
} ActionType;


typedef struct {
    ActionType type;
    u16 x;
    u16 y;
} Action;


static string
action_str(const Action& a) {
    switch (a.type) {
        case ActionMoveUp: return "W";
        case ActionMoveRight: return "D";
        case ActionMoveDown: return "S";
        case ActionMoveLeft: return "A";
        case ActionPass: return "Z";
        case ActionRotateCW: return "E";
        case ActionRotateCCW: return "Q";
        case ActionUseWheels: return "F";
        case ActionUseDrill: return "L";
    }
}


static inline u32
mdist(u32 a, u32 b) {
    return abs(i32(POSX(b)) - i32(POSX(a))) + abs(i32(POSY(b)) - i32(POSY(a)));
}


typedef struct {
    u32 pos;
    vector<ActionType> path;
} find_path_state;


typedef struct {
    ActionType action;
    i32 x;
    i32 y;
} Movement;


static Movement valid_moves[] = {
    {ActionMoveUp, 0, 1},
    {ActionMoveRight, 1, 0},
    {ActionMoveDown, 0, -1},
    {ActionMoveLeft, -1, 0},
};


static vector<ActionType>
find_path(u32 origin, u32 goal, const set<u32>& grid) {
    auto comp = [goal](const find_path_state& a, const find_path_state& b) {
        u32 va = a.path.size() + mdist(a.pos, goal);
        u32 vb = b.path.size() + mdist(b.pos, goal);
        return va > vb;
    };

    priority_queue<find_path_state, vector<find_path_state>, decltype(comp)>
    fringe(comp);
    set<u32> visited;

    fringe.push({origin});

    while (!fringe.empty()) {
        auto state = fringe.top();
        fringe.pop();

        if (state.pos == goal) {
            return state.path;
        }

        if (visited.find(state.pos) != end(visited)) {
            continue;
        }
        visited.emplace(state.pos);

        for (auto mv : valid_moves) {
            u32 x = POSX(state.pos) + mv.x;
            u32 y = POSY(state.pos) + mv.y;
            u32 pos = PACK_POS(x, y);
            if (grid.find(pos) != grid.end()) {
                auto path = state.path;
                path.push_back(mv.action);
                fringe.push({pos, path});
            }
        }
    }

    return {};
}


static vector<ActionType>
find_closest(u32 origin, set<u32> pending, const set<u32>& grid) {
    deque<u32> fringe;
    fringe.emplace_back(origin);
    set<u32> visited;

    vector<ActionType> best_path;
    u32 best_target = origin;
    u32 tries = 0;

    while (!pending.empty() && !fringe.empty()) {
        u32 pos = fringe.front();
        fringe.pop_front();

        if (visited.find(pos) != visited.end()) {
            continue;
        }
        visited.emplace(pos);

        auto it = pending.find(pos);
        if (it != pending.end()) {
            pending.erase(it);

            auto path = find_path(origin, pos, grid);
            if (best_path.empty() || path.size() < best_path.size()) {
                best_path = path;
                best_target = pos;
            }

            if (++tries > 25) {
                break;
            }
        }

        for (auto mv : valid_moves) {
            u32 x = POSX(pos) + mv.x;
            u32 y = POSY(pos) + mv.y;
            u32 pos = PACK_POS(x, y);
            fringe.emplace_back(pos);
        }
    }

    // fprintf(stderr, "  best (%u,%u)\n", POSX(best_target), POSY(best_target));
    return best_path;
}


static void
handle_sigint(i32 sig) {
    exit(1);
}


static void
dump_bot(const vector<u32>& bot) {
    for (auto p : bot) {
        fprintf(stderr, "(%u,%u),", POSX(p), POSY(p));
    }
    fprintf(stderr, "\n");
}


u32
solve(Problem* problem, u32 ans_size, char* ans) {

    signal(SIGINT, handle_sigint);

    ans[0] = 0;

    set<u32> grid;

    u16* pgrid = problem->grid;
    u32 nsize = problem->grid_size * 2;
    for (u32 i = 0; i < nsize; i+=2) {
        grid.emplace(PACK_POS(pgrid[i], pgrid[i+1]));
    }

    vector<u32> bot;
    u16 x = problem->posx;
    u16 y = problem->posy;
    bot.emplace_back(PACK_POS(x, y));
    bot.emplace_back(PACK_POS(x+1, y-1));
    bot.emplace_back(PACK_POS(x+1, y));
    bot.emplace_back(PACK_POS(x+1, y+1));

    bot = rotate_bot(bot, problem->rotation);

    set<u32> pending = grid;

    for (auto p : bot) {
        pending.erase(p);
        // auto it = pending.find(p);
        // if (it != end(pending)) {
        //     pending.erase(it);
        // }
    }

    string ans_path;

    while (!pending.empty()) {
        // fprintf(stderr, "at (%u,%u) pending %lu\n", POSX(bot[0]), POSY(bot[0]), pending.size());
        auto path = find_closest(bot[0], pending, grid);

        #if 0
        string debug;
        for (auto action : path) {
            debug.append(action_str(Action{action}));
        }
        u32 pos = bot[0];
        fprintf(stderr, "(%u,%u) to closest: %s\n", POSX(pos), POSY(pos), debug.c_str());
        #endif

        if (path.empty()) {
            break;
        }

        for (auto action : path) {
            auto& m = valid_moves[action];

            bot = move_bot(bot, m.x, m.y);

            ans_path.append(action_str(Action{action}));

            for (auto p : bot) {
                pending.erase(p);
            }

            break; // re-eval after one step
        }
    }

    strncpy(ans, ans_path.c_str(), ans_size);
    ans[ans_size-1] = '\0';

    return 0;
}
