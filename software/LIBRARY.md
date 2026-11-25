# Loading Deep Thought's library

Lookup and spoken questions search one file, `software/content.db`. Three things go in it.

| What | Where it comes from | How it gets in |
|---|---|---|
| Her own notes | The Knowledge Base and each game's "How to play" | `python tools/build_notes.py` (already done once) |
| Your own books and the free official rules | Files you put on the box | The Library web page, or the folders below |
| Every Magic card and ruling | Scryfall's free download | `python dt_content.py fetch-mtg content` |

All commands are run in `software/` with `.venv\Scripts\python` on Windows or
`python3` on the Pi.

## The easy way: upload from a browser

1. Start Deep Thought.
   You should see the Home screen.
2. Tap **Settings**, then **Phones**, then press the button until the page says **Library**.
   You should see a square code and an address.
3. Open that address on the computer that has the book.
   You should see a page titled Library.
4. Pick the game the book belongs to.
5. Tick **DM only** if it is an adventure or campaign book.
6. Choose the file and press **Upload**.
   You should see "… is loaded" and a count of sections.
7. On the box, open **Lookup** and search for a word from the book.
   You should see the book's name and page in the results.

Works for PDF, EPUB (without copy protection), text and Markdown, up to 100 MB. A bigger
book is too much for the Pi to read by itself: load it on the PC with the folder way below,
then copy `content.db` to the box.

## The folder way

Put files here, then run `python dt_content.py sync content`:

```
software/content/free/<game>/     official free downloads
software/content/mine/<game>/     books you own
software/content/mine/<game>/campaigns/    adventures: DM only
```

`<game>` is the game's id: `killteam`, `wh40k`, `dnd`, `mtg`, `risk`, or the id of any game
you have added. A new folder name is accepted as a new game.

Run `python dt_content.py stats` to see what is loaded.

## Things to know

- A scanned PDF with no text layer cannot be searched. The loader says "NO TEXT FOUND".
  Run it through OCR first.
- Two-column pages and stat tables can read out of order. The page number is still right.
- Files in a `campaigns` folder never show to players and are never sent to the cloud
  unless DM mode is unlocked.
- A spoken or typed question sends the question and up to three short excerpts to the
  cloud model, if you have set a key. Lookup sends nothing anywhere.
- `content/` and `content.db` are never put in git.
- Copy `content.db` to the Pi with the rest of `software/`. Building it on the PC is much
  faster than on a Pi 2. Close Deep Thought and let the loader finish before copying: while
  either is running, the newest changes sit in `content.db-wal` beside it.

## Tested, and not

The Magic download was run against the real Scryfall service on 21 November 2026: 35,892
cards and 80,928 rulings loaded, and cards open in Lookup. (Scryfall had changed its file
format; the loader now reads both the old and the new.) Run `fetch-mtg` again whenever you
want newer cards.

The loader has not yet met a real rulebook PDF or the real Magic rules file. Tell me what
it says the first time you load each.
