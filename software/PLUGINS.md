# Adding a game to Deep Thought

A game is a folder: `software/deepthought/games/<id>/`. There are two kinds.

## 1. A data-only game (most board games)

Two files, no code. Copy `games/tally/` and edit.

`game.json`:

```json
{
  "id": "catan",
  "name": "Catan",
  "blurb": "Trade, build, first to ten",
  "order": 60,
  "players": [3, 4],
  "phases": ["Roll", "Trade", "Build"],
  "trackers": [{"name": "Points", "start": 2, "step": 1, "min": 0, "max": null}],
  "win": {"tracker": "Points", "at": 10},
  "lowest_wins": false
}
```

`win` ends the game when anybody's count reaches `at`, and that player wins. With
`"lowest_wins": true` the game still ends when anybody reaches `at`, but whoever is lowest
at that moment wins (Hearts: ends at 100, lowest score wins). A game is never over before
anything has been scored. A `game.json` that could not be played (fewest players above
most, a `min` that is not a number, a `win` with no `at`) is left out of the list and
reported, not loaded.

`teach.json`: a list of `{"title": ..., "text": ...}` steps that teach the game **in your
own words**. Never paste text from a rulebook. The rulebook itself goes in
`content/mine/<id>/` and is searched by Lookup.

**Teach as we play.** A step may also say when it should come up during a real game:

```json
{"title": "Attacking", "text": "...", "after": "phase:attack"}
{"title": "Taking a territory", "text": "...", "trigger": "capture"}
```

- `after`: this step waits, in its place in the order, until that happens.
- `trigger`: this step comes up once, the first time that happens, whenever it is.
- The value is an event name (what a button on the play screen sends), or `phase:<key>`
  for "the game has just entered that phase", or a mark the game raises itself from
  `Game.marks` (Magic raises `knockout` and `warning`), or a list of those.
- A step with no `title` or `text`, and a mark that is not a string, are ignored. A
  `teach.json` that will not parse teaches nothing; it does not stop the box.
- Steps with neither come straight after the step before them, so the opening steps are
  read out before the first turn.

Set up then offers **Teach: Off / As we play**. With it on, each step appears as a card
over the play screen and is read aloud if she has a voice. `deepthought/guide.py` is the
whole mechanism. A game with its own Mode option (Kill Team, 40k) is left alone.

The `id` must match the folder name. The blurb must fit a tile: about 28 characters.

## 2. A game with its own rules and screens

Add `plugin.py` with `class Plugin(Game)`. Read `games/risk/` first: it is the reference.

| File | Holds |
|---|---|
| `game.json` | id, name, blurb, order |
| `rules.py` | Pure arithmetic. No pygame. Easy to test. |
| `plugin.py` | `class Plugin(Game)` and the screens |
| `teach.json` | "How to play" steps, own words |
| `shots.py` | `shots(app, snap)`: draws every screen for the screenshot run |
| `__init__.py` | empty |

Tests go in `software/tests/test_<id>.py`, a plain script in the style of
`tests/test_engine.py` (a `check(name, cond, detail)` function, last line prints
`N failed`). Run with `software/.venv/Scripts/python tests/test_<id>.py`.

### What the engine gives you (`deepthought/engine.py`)

- `Game`: the base class. Fill in `new_state`, `apply`, `over`, `strip`, `play_screen`;
  optionally `options`, `press`, `active`, `phase`, `phases`, `leader`, `standings`,
  `scoreboard`, `phone`, `marks`.
- State is a plain dict (numbers, strings, lists, dicts) so it saves as JSON.
- `apply(state, ev)` changes the state for one event and returns a list of sentences
  for Deep Thought to say. `raise ValueError("...")` to refuse an event: the state is
  restored and the message is shown. Every rule the box enforces lives here.
- `Session.do(ev="...", ...)` applies an event, logs it, saves, fires reminders.
  `Session.undo()` steps back one event. You never save or snapshot yourself.
- `phase(state)` returns a short key; `phases()` lists `(key, name)` pairs. Players hang
  their own reminders off these. `quiet_phases = ("wait",)` names phase keys that carry no
  reminders at all, not even "Every phase" ones (D&D: the enemies' turns).
- `marks(before, state, ev)` returns extra names a teaching step may wait on, for moments
  that are not one event: `["knockout"]` when this event put a player out by any route.
  `before` is the state as it was. The default returns `[]`.
- `scoreboard(session)` is what the shared web page shows; `phone(session, seat)` is
  what one player's phone shows. Neither may leak hidden information.
- **A phone action that asks for a value.** An action is normally `{"label", "ev"}`: one
  tap sends the event. Add `"ask": "a question"` and the phone first asks the player for a
  short piece of text, then sends the event with it added as `text`:

  ```python
  {"label": "Name Secondary 1", "ev": {"ev": "sec", "side": seat, "op": "name", "slot": 0},
   "ask": "Which secondary is it?", "choices": ["Grobnar Hunt", "Hold The Bridge"], "max": 24}
  ```

  `choices` (optional) are offered as buttons; the player may always type instead. `max`
  (optional, default 40) is the most letters kept. The text is tidied to single spaces
  before your `apply` sees it; an empty one never reaches you. `apply` decides whether the
  text is acceptable and raises `ValueError` as usual: that sentence is shown on the phone
  **and on the box**, so never put a secret in it. Used by 40k (naming a secondary) and
  Kill Team (the secret Tac Op). Anything a player types that the others must not see
  goes in the state, and only that seat's `phone()` may show it. Characters that cannot
  be drawn or saved (a NUL, an escape, half of a broken emoji) are dropped before `apply`
  sees the text; tidy a typed name the same way in your own rules, as `tac_clean` does.
- **One phone to a seat.** The first phone to open a seat in a game holds it: only that
  phone is sent `phone(session, seat)` or may press that seat's actions. A new game, or
  the box starting again, frees every seat; so does Settings, Phones, Free the seats.
  The web server does this; a plugin has nothing to do for it.

### What the screens give you (`deepthought/screens/common.py`, `widgets.py`, `theme.py`)

- `PlayBase(app, session)`: base for play screens. Gives `self.do(**ev)`, `self.undo()`,
  `self.more()` (the shared menu: rules, reminders, spinner, clock, lookup, end game),
  the top strip from `Game.strip`, the turn pill, the ring in the active player's
  colour, and the button: press = `Game.press`, double = undo, hold = talk.
- The button, for any screen you write. The hardware always sends `"press"` first and
  then, if a second press comes inside 350 ms, `"double"`. The shell gives a double to
  the screen that received its press: if that press opened something on top, it is put
  away first; if that press closed its own screen, the double is dropped. So
  `on_button("double")` on a play screen means "take back the press just made, then
  undo one more", and a screen whose press closes it never sees a double. In tests,
  always send press then double; a double on its own cannot happen on the box.
- A fault in a screen or in `apply` no longer stops the program: the state is put back,
  the fault is written to `data/errors.log`, and she says so. Look there first.
- `row([(label, action, flex, style)], BOTTOM_Y, BOTTOM_H)`: the bottom button row.
  Styles: `"primary"` (one per screen, the main action) and `"plain"`.
- `Button(rect, label, action, style, sub, selected, dim, size)`, `Tile(rect, label,
  value, action, colour, note)`.
- `T.draw_text(surf, text, kind, size, colour, pos, anchor, max_w)`. Kinds: `head`,
  `head5` (Space Grotesk), `text`, `mid`, `bold` (Inter). Pass `max_w` so text shrinks
  or is cut rather than overflowing.
- `Pages`, `Choice`, `TextEntry`, `Setup`, `GameOver` are ready-made screens.
- `self.app.say("...")` shows a line from Deep Thought (and speaks it when she has a voice).
- `self.app.push(screen)`, `self.app.pop()`, `self.app.go_home()`.
- `self.app.library.search(query, game, dm=self.app.dm)` searches the loaded books.

### Rules for every screen

- 800x480. Colours only from `theme.py`. Nothing under 22 px (the theme enforces it).
- Every tappable thing at least 64 px tall and wide, inside the screen, below the 60 px
  strip, not overlapping another. `tests/test_engine.py` has a `screen_ok()` check; use it.
- Never show state by colour alone: add a word, a thick edge or a bar as well.
- One `primary` button per screen. The physical button always does that action.
- Typing happens on a phone. `TextEntry` is for a short name or search term only.
- Draw only in `build()` and `draw_body()`. No timers, no threads, no sleeping.

### Rules for the words

- Deep Thought is "she": a vast, weary, dry intellect, mildly put out at being asked.
  Short sentences. No exclamation marks, no "awesome", no "let's go".
- She teaches in her own words. **No text from paid rulebooks, codexes, adventures or
  cards, ever** – not in code, data, tests or comments. Mechanics restated as plain
  sums are fine. Unit stats, points values and card text are not: the box sends the
  player to their own book or card for those.
- When she is not sure of a rule, she says the card or the book decides.
