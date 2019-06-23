#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <deque>
#include <map>
#include <queue>
#include <set>
#include <string>
#include <sstream>
#include <vector>

using namespace std;

typedef int16_t i16;
typedef int32_t i32;
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;


extern "C" {

    typedef enum : char {
        BoosterManips = 'B',
        BoosterWheels = 'F',
        BoosterDrill = 'L',
        BoosterClone = 'C',
        BoosterTeleport = 'R',
        BoosterSpawn = 'X',
    } BoosterType;

    typedef struct {
        u16 posx;
        u16 posy;
        BoosterType type;
    } Booster;

    typedef struct {
        u16 posx;
        u16 posy;
        u8 rotation; // r * 90
        u32 grid_size; // len(tuples)
        u16* grid;
        u32 booster_size;
        Booster* boosters;
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

static vector<u32>
attach_manip(const vector<u32>& bot, u8 rotation, i16 x, i16 y) {
    auto res = bot;
    u16 ox = POSX(bot[0]);
    u16 oy = POSY(bot[0]);
    res.push_back(PACK_POS(ox + x, oy + y));
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
    ActionAttachManip,
    ActionUseWheels,
    ActionUseDrill,
} ActionType;


typedef struct {
    ActionType type;
    i16 x;
    i16 y;
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
        case ActionAttachManip: {
            ostringstream so;
            so << "B(" << a.x << "," << a.y << ")";
            return so.str();
        }
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


static Movement rotation_moves[] = {
    {ActionRotateCW, 1},
    {ActionRotateCCW, 3},
};



static vector<ActionType>
find_path(u32 origin, u32 goal, const set<u32>& grid, i32 wheels) {
    auto comp = [goal, wheels](const find_path_state& a, const find_path_state& b) {
        u32 ma = mdist(a.pos, goal);
        u32 mb = mdist(b.pos, goal);
#if 0
        i32 ta = wheels - i32(a.path.size());
        if (ta > 0) {
            ma -= ta / 2;
        }

        i32 tb = wheels - i32(b.path.size());
        if (tb > 0) {
            mb -= tb / 2;
        }
#endif
        u32 va = a.path.size() + ma;
        u32 vb = b.path.size() + mb;
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

        i32 wheels_left = max(0, wheels - i32(state.path.size()));

        for (auto mv : valid_moves) {
            u32 x = POSX(state.pos) + mv.x;
            u32 y = POSY(state.pos) + mv.y;
            u32 pos = PACK_POS(x, y);
            if (grid.find(pos) != grid.end()) {
                auto path = state.path;
                path.push_back(mv.action);

                if (wheels_left) {
                    x += mv.x;
                    y += mv.y;
                    u32 pos2 = PACK_POS(x, y);
                    if (grid.find(pos2) != grid.end()) {
                        pos = pos2;
                    }
                }

                fringe.push({pos, path});
            }
        }
    }

    return {};
}


typedef struct {
    i32 score;
    vector<ActionType> path;
} ClosestResult;


static vector<vector<ActionType>>
find_closest(u32 origin, set<u32> pending, const set<u32>& grid, const map<u32, BoosterType>& grid_boosters,
    map<BoosterType, u32> active_boosters) {

    for (const auto& p : grid_boosters) {
        BoosterType t = p.second;
        u32 pos = p.first;
        if (t != BoosterSpawn) {
            pending.insert(pos);
        }
    }

    const u32 wheels = active_boosters[BoosterWheels];

    deque<u32> fringe;
    fringe.emplace_back(origin);
    set<u32> visited;

    auto best_comp = [](const ClosestResult& a, const ClosestResult& b) {
        return a.score < b.score;
    };

    priority_queue<ClosestResult, vector<ClosestResult>, decltype(best_comp)>
    best_results(best_comp);
    u32 tries = 0;

    static const i32 neigh_moves[][2] = {
        {-1,-1}, {0,-1}, {1,-1},
        {-1, 0},         {1, 0},
        {-1, 1}, {0, 1}, {1, 1},
    };

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

            i32 tunnels = 0;
            for (const auto& mv : neigh_moves) {
                u32 x = POSX(pos) + mv[0];
                u32 y = POSY(pos) + mv[1];
                u32 pos = PACK_POS(x, y);
                if (grid.find(pos) == grid.end()) {
                    tunnels += 2;
                }
                else if (pending.find(pos) == pending.end()) {
                    tunnels += 1;
                }
            }

            u8 has_booster = grid_boosters.find(pos) != grid_boosters.end() ? 1 : 0;

            auto path = find_path(origin, pos, grid, wheels);
            if (path.empty()) {
                continue;
            }

            i32 score = 50 * i32(has_booster) + tunnels - path.size();

            if (best_results.empty()) {
                best_results.push(ClosestResult{score, path});
                tries = 0;
            }
            else {
                auto& best = best_results.top();
                if (score > best.score) {
                    best_results.push(ClosestResult{score, path});
                    tries = 0;
                }
            }

            if (++tries > 20 || best_results.size() > 10) {
                break;
            }
        }

        for (const auto& mv : neigh_moves) {
            i32 x = POSX(pos) + mv[0];
            i32 y = POSY(pos) + mv[1];
            u32 pos = PACK_POS(x, y);
            if (grid.find(pos) != grid.end()) {
                fringe.emplace_back(pos);
            }
        }
    }

    if (best_results.empty()) {
        return {};
    }

    vector<vector<ActionType>> res;
    while (!best_results.empty()) {
        auto& best = best_results.top();
        res.push_back(best.path);
        best_results.pop();
    }

    return res;
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

    map<u32, BoosterType> grid_boosters;
    for (u32 i = 0; i < problem->booster_size; i++) {
        const auto& t = problem->boosters[i];
        grid_boosters[PACK_POS(t.posx, t.posy)] = t.type;
    }

    map<BoosterType, u32> booster_bag;
    map<BoosterType, u32> active_boosters;

    vector<u32> bot;
    u16 x = problem->posx;
    u16 y = problem->posy;
    bot.emplace_back(PACK_POS(x, y));
    bot.emplace_back(PACK_POS(x+1, y-1));
    bot.emplace_back(PACK_POS(x+1, y));
    bot.emplace_back(PACK_POS(x+1, y+1));

    bot = rotate_bot(bot, problem->rotation);

    set<u32> pending = grid;

    auto sweep = [&grid, &pending, &grid_boosters, &booster_bag] (const vector<u32>& bot) {
        auto it = grid_boosters.find(bot[0]);
        if (it != grid_boosters.end()) {
            BoosterType t = it->second;
            if (t != BoosterSpawn) {
                booster_bag[t] += 1;
                grid_boosters.erase(it);
            }
        }

        for (u32 i = 0; i < 4; i++) {
            auto p = bot[i];
            pending.erase(p);
        }
        for (u32 i = 4; i < bot.size(); i++) {
            auto p = bot[i];
            if (grid.find(p) == grid.end()) {
                break;
            }
            pending.erase(p);
        }
    };

    sweep(bot);

    string ans_path;

    auto tick_with_action = [&active_boosters, &ans_path] (Action action) {
        ans_path.append(action_str(action));

        for (const auto& it : active_boosters) {
            if (it.second > 0) {
                active_boosters[it.first] -= 1;
            }
        }
    };

    u32 steps = 0;

    while (!pending.empty()) {
        auto boosters = active_boosters;
        u8 did_boost = 0;
        u8 did_rotate = 0;

        for (const auto& it : booster_bag) {
            BoosterType t = it.first;
            u32 n = it.second;
            if (n == 0) continue;
            if (boosters[t] > 0) continue;

            if (t == BoosterManips) {
                booster_bag[it.first] -= 1;
                i16 x = 3 - i16(bot.size());
                i16 y = 0;
                tick_with_action(Action{ActionAttachManip, x, y});
                bot = attach_manip(bot, 0, x, y);
                did_boost = 1;
                break;
            }
            else if (t == BoosterWheels) {
                booster_bag[it.first] -= 1;
                tick_with_action(Action{ActionUseWheels});
                active_boosters[t] = 50;
                did_boost = 1;
                break;
            }
        }

        if (did_boost) {
            continue;
        }

        // for (const auto& mv : rotation_moves) {
        //     auto rbot = rotate_bot(bot, mv.x);
        //     u32 touched = 0;
        //     for (auto p : rbot) {
        //         if (pending.find(p) != pending.end()) {
        //             touched++;
        //         }
        //     }
        //
        //     if (touched > 2) {
        //         ans_path.append(action_str(Action{mv.action}));
        //         bot = rbot;
        //         sweep(bot);
        //
        //         did_rotate = 1;
        //         break;
        //     }
        // }

        if (did_rotate) {
            fprintf(stderr, "did rotate\n");
            continue;
        }

        auto best_closest = find_closest(bot[0], pending, grid, grid_boosters, boosters);

        if (best_closest.empty()) {
            break;
        }

        // random
        auto path = best_closest[0];

        for (auto action : path) {
            auto& m = valid_moves[action];
            auto newbot = move_bot(bot, m.x, m.y);

            if (grid.find(newbot[0]) == grid.end()) {
                break;
            }

            bot = newbot;
            sweep(bot);

            tick_with_action(Action{action});

            if (boosters[BoosterWheels] > 0) {
                auto newbot = move_bot(bot, m.x, m.y);
                if (grid.find(newbot[0]) != grid.end()) {
                    bot = newbot;
                    sweep(bot);
                    steps = 0;
                    break; // re-eval
                }
            }

            if (++steps > 2) {
                steps = 0;
                break; // re-eval
            }
        }
    }

    if (!pending.empty()) {
        return 1;
    }

    strncpy(ans, ans_path.c_str(), ans_size);
    ans[ans_size-1] = '\0';

    // fprintf(stderr, "answer: %s\n", ans);

    return 0;
}
