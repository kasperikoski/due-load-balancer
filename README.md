# Due Load Balancer

Version: 0.0.1

Due Load Balancer is an Anki add-on for gently spreading overdue review cards over a future date range.

It is meant for situations where a review backlog has grown too large to handle comfortably. This can happen after a break from studying, after importing or reorganizing decks, or after enabling a rescheduling feature such as FSRS reschedule cards on change. Instead of facing hundreds of overdue reviews at once, you can redistribute them evenly across a chosen number of days. For example, if you have 400 overdue review cards and spread them over 100 days, the add-on schedules about 4 of those cards per day.

> [!IMPORTANT]
> Before running this add-on, read the [Safety note](#safety-note).
>
> **Back up your Anki collection before use.**<br>
> **Varmuuskopioi Anki-kokoelmasi ennen käyttöä.**<br>
> **Säkerhetskopiera din Anki-samling före användning.**<br>
> **Sichern Sie Ihre Anki-Sammlung vor der Verwendung.**<br>
> **Sauvegardez votre collection Anki avant utilisation.**<br>
> **Esegui un backup della tua collezione Anki prima dell’uso.**<br>
> **Haz una copia de seguridad de tu colección de Anki antes de usarlo.**<br>
> **Faça uma cópia de segurança da sua coleção do Anki antes de usar.**<br>
> **Перед использованием создайте резервную копию своей коллекции Anki.**<br>
> **使用前请备份你的 Anki 集合。**<br>
> **使用前に Anki コレクションをバックアップしてください。**


## What it does

The add-on changes only the next due day of selected overdue review cards.

It does not intentionally change card interval, ease, reps, lapses, note content, deck, tags, new cards, or learning cards. Anki will still update normal sync metadata because the card records are saved.

## Main features

* Select decks and subdecks from a tree view.
* Select all visible decks or unselect all decks.
* Optionally show only decks that currently contain due review cards.
* Collect selected overdue review cards into one shared pool across the selected decks.
* By default, keep cards in their current due order, so the oldest overdue cards are placed earlier in the new schedule.
* Optionally shuffle cards before spreading.
* Choose how many days the backlog should be spread over.
* Choose the first rescheduled day with either a day number or a calendar date.
* The day number and calendar picker stay in sync.
* `Days from today = 0` means today.
* `Days from today = 1` means tomorrow.
* Choose a distribution profile: even, front-loaded, back-loaded, or bell curve.
* Adjust curve strength for non-even distribution profiles.
* Hide curve strength automatically when the even profile is selected.
* Keep at least one moved card on each day when there are enough cards to do so.
* Spread sparse backlogs across the full selected range when there are fewer cards than days.
* Open a preview window before applying changes.
* Preview the daily card count, relative load and visual load bars.
* Confirm the action before cards are rescheduled.
* User-editable `config.json`.
* JSON language files in `addon/lang/`.

## Card order

By default, Due Load Balancer does not process decks one by one. It gathers all selected overdue review cards into a single pool and orders them by their current due day.

This means that a card overdue by six months is placed earlier in the new schedule than a card overdue by four months, even if they are in different decks. If multiple cards have the same due day, Anki's card id is used as the secondary order.

If you enable shuffle, the selected cards are mixed before they are spread across the chosen date range.

## Distribution profiles

Due Load Balancer can spread selected overdue review cards using different distribution profiles.

```text
even          Keeps the daily load as even as possible.
front_loaded  Puts more moved cards near the beginning of the range.
back_loaded   Puts more moved cards near the end of the range.
bell_curve    Puts more moved cards near the middle of the range.
```

`curve_strength` controls how strongly the non-even profiles are shaped. `1.0` is a gentle default. Higher values make the curve more pronounced. The strength setting does not affect the even profile.

When there are at least as many cards as days, the scheduler tries to place at least one moved card on every day. When there are fewer cards than days, the cards are spread across the full range as evenly as possible.

## Preview

The preview window shows what the operation will do before any cards are changed.

It shows:

* the date
* the relative start label
* the number of moved cards for that day
* a visual load bar
* total moved cards
* minimum, maximum and average moved cards per day
* the selected distribution profile

The load bar is relative to the busiest day in the preview. It only shows the cards moved by this operation, not Anki's full future review load.

## Installation for local testing

Copy the contents of the `addon` folder into a folder inside Anki's `addons21` directory, for example:

```powershell
mkdir "$env:APPDATA\Anki2\addons21\anki_due_load_balancer"
Copy-Item -Recurse .\addon\* "$env:APPDATA\Anki2\addons21\anki_due_load_balancer\"
```

Restart Anki. The add-on appears under:

```text
Tools -> Due Load Balancer
```

## Building the .ankiaddon file

From the project root:

```powershell
python .\scripts\build_ankiaddon.py
```

The package will be created in `dist/`.

AnkiWeb expects the `.ankiaddon` archive to contain `__init__.py` and the other add-on files directly at the archive root, not inside an extra parent folder.

## Configuration

The default configuration lives in:

```text
addon/config.json
```

Important values:

```json
{
  "project": {
    "display_name": "Due Load Balancer",
    "version": "0.0.1",
    "menu_label_override": ""
  },
  "ui": {
    "language": "en",
    "window_width": 760,
    "window_height": 780,
    "preview_window_width": 620,
    "preview_window_height": 560,
    "date_format": "%d.%m.%Y"
  },
  "defaults": {
    "spread_over_days": 30,
    "start_after_days": 1,
    "shuffle_cards_before_spreading": false,
    "distribution_profile": "even",
    "curve_strength": 1.0,
    "show_only_decks_with_due_reviews": true
  }
}
```

To enable Finnish UI text by default, set:

```json
{
  "ui": {
    "language": "fi"
  }
}
```

## Adding languages

Add a new JSON file under:

```text
addon/lang/
```

For example:

```text
addon/lang/de.json
```

Then set the language code in `config.json`:

```json
{
  "ui": {
    "language": "de"
  }
}
```

If a translation key is missing, the add-on falls back to English.

## Repository

The project repository is:

https://github.com/kasperikoski/anki-due-it-now

## Development notes

The core scheduling logic is isolated in `addon/scheduler.py`, so it can be tested outside Anki.

Run the included scheduler tests with:

```powershell
python -m pytest
```

Build the add-on package with:

```powershell
python .\scripts\build_ankiaddon.py
```

## Safety note

Before doing a reschedule, create a backup and sync Anki. The add-on is intentionally conservative, but backlog spreading is still a mass scheduling operation.

After rescheduling a large number of cards, it is also a good idea to run **Tools → Check Database** in Anki. This is not required for normal use, but it can help verify and optimize the collection after a large scheduling change.
