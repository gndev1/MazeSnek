
# Getting Started with MazeSnek and MoltMaze

This guide is the thorough walkthrough for new users and new developers.

It explains:

- what MoltMaze is
- what kinds of problems the game throws at a bot
- how MazeSnek works internally
- how MazeSnek approaches navigation, equations, retries, and timing
- how to use MazeSnek as the starting point for your own bot

If you only need installation and basic usage, go back to **README.md**.

---

## What is MoltMaze?

MoltMaze is a bot-oriented maze game where movement is not performed by simply sending `up`, `down`, `left`, or `right`.

Instead, on each turn:

- every direction has an associated challenge
- the bot must decide which direction it wants
- the bot must solve that direction's challenge
- the bot submits the answer
- if correct, the move happens and the turn advances

That means MoltMaze is not just pathfinding.

It combines:

- maze navigation
- challenge solving
- API communication
- timing and retry logic
- state freshness discipline

A bot that is good at only one of those things will still fail.

---

## The Core Challenge of the Game

At first glance, the goal is straightforward:

- find the exit
- move there
- go to the next stage

But the game creates difficulty in multiple layers.

### 1. Navigation

The bot has to understand the maze and decide where to go.

### 2. Equation solving

The bot cannot simply request a move. It must solve the current challenge bound to that move.

### 3. State freshness

The server uses turn-based state. A challenge belongs to a specific turn. The bot must not treat stale action data as current truth.

### 4. Timing

Servers can rate-limit requests. A bot that spams or retries badly will fail even if its logic is correct.

### 5. Future complexity

MoltMaze is intended to grow. Even if the current stage format is simple, future stages may introduce chunking, enemies, collectibles, floors, and other mechanics. A good bot design should be extensible.

---

## What MazeSnek Is

MazeSnek is a deliberately readable reference implementation.

It is not trying to be the most optimized or most advanced bot possible.

Instead, it is trying to show the full end-to-end flow clearly:

1. connect to the API
2. normalize state
3. represent the maze internally
4. pathfind
5. choose a move
6. solve the move challenge
7. submit the result
8. recover from errors and continue

That makes it useful both as a working bot and as an educational project.

---

## How the MazeSnek Loop Works

At a high level, MazeSnek does:

```text
FETCH STATE -> PARSE STATE -> PATHFIND -> CHOOSE DIRECTION -> SOLVE CHALLENGE -> SUBMIT ANSWER -> HANDLE RESPONSE -> REPEAT
```

Each stage matters.

---

## Step 1: Fetch State

MazeSnek asks the server for the current run state.

The response typically includes:

- run id
- level
- turn
- player position
- goal position
- maze representation
- actions
- score
- optional metadata depending on server version

This is the bot's current world snapshot.

A very important rule:

**do not assume old state is still valid after a move**

Because MoltMaze is turn-based, the correct action set for turn N is not the correct action set for turn N+1.

---

## Step 2: Parse and Normalize State

Different server versions can evolve over time. MazeSnek therefore tries to normalize the raw payload into a stable internal representation.

The parser's job is to extract:

- current `(x, y)`
- goal `(x, y)`
- maze layout
- action objects
- equation text
- answer format
- optional challenge metadata

This is one of the most important design choices in the bot.

By keeping parsing separate from the rest of the logic, the rest of the bot can stay stable even if the raw payload changes slightly.

---

## Step 3: Build an Internal Maze Model

MazeSnek needs a model of the maze that pathfinding can use.

Conceptually, the maze becomes a graph:

- each reachable tile is a node
- each legal move between neighboring tiles is an edge

That means the bot can think in terms of graph traversal instead of raw API JSON.

Even in the current simpler versions of the game, this is the right abstraction. It will matter even more when MoltMaze grows to include more advanced layouts.

---

## Step 4: Pathfinding

MazeSnek currently uses **Breadth-First Search (BFS)**.

Why BFS?

- it is easy to understand
- it is deterministic
- it guarantees the shortest path in an unweighted maze
- it is good enough for the current problem size

BFS explores outward layer by layer:

1. start at the current tile
2. inspect all neighboring tiles
3. inspect their neighbors
4. continue until the goal is found

That means the first time BFS reaches the goal, it has found a shortest path.

### Example

If the path is:

```text
(4,3) -> (5,3) -> (6,3) -> (6,4) -> goal
```

MazeSnek only needs the **next step** to determine the immediate direction.

---

## Step 5: Choose a Direction

Once the path is known, MazeSnek compares:

- current tile
- next tile

That difference becomes one of:

- up
- down
- left
- right

Example:

- current: `(4,3)`
- next: `(5,3)`
- direction: `right`

Now the bot knows which action challenge it needs to solve.

---

## Step 6: Solve the Equation or Challenge

This is the second major part of the bot.

MoltMaze gates movement behind challenges. In current phases, these are primarily text-based mathematical challenges.

MazeSnek includes a deterministic solver that can handle the server's challenge formats.

### Types of challenge complexity

Depending on the server version and stage difficulty, challenges may include:

- basic arithmetic
- nested expressions
- negative values
- modulo
- variable assignments
- multiple parts
- ordered multi-value answers

### Single answer

Example:

```text
(5 + 3) * 6
```

The solver evaluates that to:

```text
48
```

### Ordered multi-part answers

Some challenge sets require multiple answers in a fixed order.

If the action format says:

```text
ordered_integer_list
```

MazeSnek must submit:

```text
12,45,99
```

with no spaces.

That formatting requirement matters. A correct set of numbers in the wrong format can still fail.

### Solver design goals

MazeSnek’s solver is designed to be:

- deterministic
- safe
- understandable
- adaptable to server-side evolution

It supports:

- nested expressions
- negative values
- modulo
- variable substitution
- multi-part outputs

The solver code is intentionally kept readable so new developers can follow how an equation is interpreted step by step.

---

## Step 7: Submit the Answer

Once the solver returns the answer for the chosen direction, MazeSnek submits it back to the server.

If the answer matches the accepted stored answer for a traversable direction:

- the move is accepted
- the run position changes
- the turn advances
- a new action set exists for the next turn

If not:

- the move fails
- the turn may remain the same
- the bot needs to refresh and recover

This is why immutable per-turn challenges matter so much on the server side. Without that, bots can solve the visible challenge correctly and still be rejected if the server changes the accepted answer underneath them.

---

## Step 8: Handle Responses and Retry Conditions

MazeSnek expects a live server to sometimes reject or delay it.

It handles several important response classes.

### Success

This is the easy case. Continue normally.

### Invalid answer

Possible causes:

- solver mismatch
- stale state
- wrong chosen direction
- server inconsistency

MazeSnek refreshes state and continues rather than crashing immediately.

### Rate limiting (`HTTP 429`)

MoltMaze can pace clients.

MazeSnek therefore:
- waits
- honors retry timing when available
- retries safely

### Network or transient failures

MazeSnek treats these as retriable conditions where possible.

This is important because a bot operating against a live server must be resilient, not brittle.

---

## The Main Difficulties MoltMaze Throws at a Bot

To design a stronger bot, it helps to think clearly about the categories of challenge.

### Navigation difficulty

The maze itself can already be nontrivial.

### Equation difficulty

Knowing where to go is not enough. The bot still has to unlock that movement.

### Timing difficulty

The server can reject poorly paced requests.

### Synchronization difficulty

A bot must stay synchronized with current-turn state.

### Future mechanic difficulty

As the game expands, the bot may need to reason about:
- limited visibility
- chunk memory
- enemies
- resources
- multi-floor traversal
- OCR/image-based challenges

MazeSnek is structured to make future upgrades possible, even if it does not solve every future mechanic yet.

---

## How MazeSnek Approaches These Problems

MazeSnek takes a modular approach.

### `client.py`
Handles HTTP communication and request/response flow.

### `state.py`
Handles normalization of server payloads.

### `pathfinding.py`
Handles navigation decisions.

### `solver.py`
Handles equations and answer formatting.

### `cli.py`
Ties the runtime loop together.

This separation is deliberate. It makes the project easier to learn from, and it makes it easier for you to swap out one subsystem without rewriting the whole bot.

---

## Why the Project Is Intentionally Clear Rather Than Clever

MazeSnek is meant to be a starting point.

That means the code should be understandable by someone who wants to learn:

- how to call a live API
- how to model state
- how to pathfind
- how to solve structured challenges
- how to build a bot loop

A highly optimized but opaque bot would be worse for that purpose.

So MazeSnek prefers:
- clear structure
- readable modules
- obvious responsibilities
- straightforward algorithms

---

## Common Pitfalls for New Bot Authors

### Reusing stale state
A move solved from old action data may fail.

### Ignoring rate limits
Correct logic with bad pacing still fails.

### Overcomplicating version one
A smaller, correct bot is more useful than a “smart” bot that desynchronizes constantly.

### Treating parsing as trivial
State normalization is one of the most important parts of keeping a bot stable as the API evolves.

---

## How to Learn From This Project

A good learning order is:

1. run MazeSnek normally
2. run it with `--debug`
3. read `client.py`
4. read `state.py`
5. read `pathfinding.py`
6. read `solver.py`
7. change one subsystem
8. test it live

Do not try to reinvent the entire bot all at once. Change one layer at a time and observe what happens.

---

## How to Fork It Into Your Own Bot

Good next experiments include:

### Replace BFS
Try:
- A*
- weighted search
- goal heuristics
- chunk-aware exploration later

### Improve the solver
Try:
- caching
- symbolic simplification
- better structured parsing
- future OCR/image support

### Add strategy
Try:
- exploration versus direct pathing
- collectible prioritization
- enemy avoidance
- chunk memory
- multi-floor planning

MazeSnek is a good starting point because these can all be done incrementally.

---

## Final Perspective

MazeSnek is not meant to be the strongest bot.

It is meant to be the clearest bot.

That makes it valuable for:
- new players
- new developers
- experimentation
- teaching
- forking

If your goal is to understand how a MoltMaze bot works and then build your own, this is exactly where you should start.
