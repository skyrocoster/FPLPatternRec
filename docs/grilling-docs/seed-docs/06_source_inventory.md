# 06 — Source Inventory

**Last checked:** 2026-09-23

## 1. Scope

This is a working inventory of **free supplementary Premier League data sources** for the project.

The FPL API is already part of the project and is intentionally not inventoried here.

The collection policy is simple:

> Collect as much structured or parseable data as possible where the record can be resolved, directly or indirectly, to a canonical project key.

Useful canonical grains include:

```text
competition / season
fixture
team
player

fixture + team
fixture + player

fixture + event
fixture + team + event
fixture + player + event

team + season
player + season
```

Do not filter fields at collection time because they do not currently appear useful for modelling.

Source-specific aggregates should still be collected where available even if lower-grain data allows them to be calculated independently.


---

# 2. Priority Summary

| Source | Priority | Best use | Main grain | Native IDs |
|---|---:|---|---|---|
| WhoScored | 1 | Detailed match event stream | event | fixture, team, player |
| FotMob | 1 | Match/player/team stats, shots, heatmaps | fixture/player/event | fixture, team, player |
| Sofascore | 1 | Player-match stats, team stats, incidents, heatmaps | fixture/player/event | fixture, team, player |
| Understat | 1 | Shot-level xG and attacking data | shot/player-match | match, team, player |
| PremierLeague.com | 1 | Official player/team totals and supplementary stats | player-season/team-season | site entities/URLs |
| StatBunker | 2 | Broad player/team statistical tables | player-season/team-season | competition plus page entities |
| Football-Data.co.uk | 2 | Match results, traditional match stats, odds | fixture/team | no strong player IDs |
| Transfermarkt | 2 | Squads, transfers, injuries, suspensions | player/team/date | player, club, competition |
| ClubElo | 2 | Historical team-strength ratings | team/date | club API name |
| FBref | Conditional | Basic/current standard stats and historical data | player/team-season | player/team URLs |
| Squawka | Conditional | Large player/team metric catalogue | player/team-season | web entities to inspect |

Priority is an implementation order, not a statement about data quality.


---

# 3. WhoScored

## Role

Primary event-level source.

WhoScored is particularly valuable because the available event stream includes individual football actions rather than only player-match aggregates.

## Access

There is no supported public developer API being used here.

The current `soccerdata` project contains an active Selenium-based WhoScored scraper:

- https://github.com/probberechts/soccerdata
- https://github.com/probberechts/soccerdata/blob/master/soccerdata/whoscored.py

Base site:

- https://www.whoscored.com/

## Known grain

```text
competition
season
fixture
event
player
team
```

## Useful native identity fields

The current scraper exposes event fields including:

```text
game_id
team_id
player_id
```

These are valuable for canonical source mapping.

## Event fields currently exposed by soccerdata

The current scraper code includes fields such as:

```text
game_id
period
minute
second
expanded_minute

type
outcome_type

team_id
team

player_id
player

x
y
end_x
end_y

goal_mouth_y
goal_mouth_z

blocked_x
blocked_y
```

There are additional event attributes / qualifiers available in the source payload.

## Collection target

For every Premier League fixture, collect the **full source event payload**, not merely selected event categories.

Potential downstream event families include:

```text
passes
shots
goals
cards
tackles
interceptions
dribbles
substitutions
touches
other qualified actions
```

## Important implementation note

WhoScored scraping is browser-oriented and therefore likely to be more operationally fragile than direct JSON endpoints.

Treat the collector as replaceable.

Store the raw match/event payload before canonical transformation.


---

# 4. FotMob

## Role

Primary structured JSON source for:

```text
fixtures
match details
player match statistics
team match statistics
shots / shot maps
league stat tables
teams
players
transfers
heatmaps
live ticker data where available
```

## Access

FotMob exposes undocumented JSON routes used by its website.

Useful current community references:

- https://github.com/ccdejene/fotmob-mcp/blob/main/docs/fotmob-api.md
- https://github.com/writeshh/FotMob-API

Base route pattern:

```text
https://www.fotmob.com/api/data/
```

## Useful routes

### Discovery

```text
GET /api/data/search/suggest
GET /api/data/allLeagues
```

### Daily fixtures

```text
GET /api/data/matches
```

Typical parameter:

```text
date
```

### League overview

```text
GET /api/data/leagues
```

Useful for:

```text
seasons
fixtures
tables
league metadata
```

### League statistical tables

```text
GET /api/data/leagueseasondeepstats
```

Typical concepts:

```text
league
season
players / teams
stat
team filter
```

Important: FotMob may use an internal season ID for deep-stat routes rather than only a display season such as `2026/2027`.

### Match details

```text
GET /api/data/matchDetails?matchId={id}
```

This should be treated as a high-value core endpoint.

Potential contents include:

```text
fixture metadata
teams
score
lineups
player statistics
team statistics
shot data / shot map references
xG information
match events
```

### Team

```text
GET /api/data/teams?id={teamId}
```

### Player

```text
GET /api/data/playerData?id={playerId}
```

### Player match history

```text
GET /api/data/playerMatches?playerId={playerId}
```

### Transfers

```text
GET /api/data/transfers
```

### Match heatmaps

Current community documentation uses a route of the form:

```text
GET /api/data/heatmap/match/{matchId}/heatmaps
```

The required heatmap URL/context can be obtained from match details.

### Live ticker

Current community tooling derives ticker data from match detail information and FotMob data URLs.

Collect if it proves useful, but it is secondary to the completed match payload.

## Native IDs

FotMob exposes useful numeric IDs for:

```text
match
team
player
league
season
```

These should make entity resolution straightforward after initial source mapping.

## Collection target

For each Premier League fixture:

```text
matchDetails
all player statistics
all team statistics
shot data
lineups
heatmaps where available
event/ticker data where useful
```

Also collect league-wide deep-stat tables because they can expose metrics not obvious in the individual match payload and provide aggregate reconciliation totals.

## Notes

The routes are undocumented implementation endpoints rather than a stable public developer contract.

Schemas should be expected to change.


---

# 5. Sofascore

## Role

Primary structured JSON source for:

```text
fixtures
lineups
player match statistics
team statistics
incidents
shot maps
heatmaps
average positions
match metadata
```

## Access

Current base URL:

```text
https://api.sofascore.com/api/v1
```

Useful current community references:

- https://github.com/apdmatos/sofascore-api
- https://github.com/Tariq-15/TacosScore/blob/main/docs/sofascore-api-reference.md
- https://github.com/federicorabanos/LanusStats/blob/main/LanusStats/sofascore.py

## Competition discovery

```text
GET /unique-tournament/{tournamentId}/seasons
```

## Fixtures by competition round

```text
GET /unique-tournament/{tournamentId}/season/{seasonId}/events/round/{roundNumber}
```

## Scheduled events

A date-based scheduled-events route is also available:

```text
GET /sport/football/scheduled-events/{date}
```

## Match

```text
GET /event/{eventId}
```

Useful fixture-level information can include:

```text
home team
away team
team IDs
kickoff
score
status
venue
referee
competition metadata
```

## Team statistics

```text
GET /event/{eventId}/statistics
```

Statistics are grouped by match period.

Common periods include:

```text
ALL
1ST
2ND
```

## Lineups and player-match statistics

```text
GET /event/{eventId}/lineups
```

This is one of the highest-value Sofascore endpoints.

The lineup payload includes:

```text
player objects
player IDs
shirt / jersey numbers
position
starter / substitute information
formation
player statistics blocks
```

Current community inspection shows a large player-statistics block embedded in lineups.

For bulk match ingestion, this is preferable to individually requesting every player's statistics.

## Single player-match statistics

```text
GET /event/{eventId}/player/{playerId}/statistics
```

This largely overlaps with the statistics included in the lineup payload.

## Incidents

```text
GET /event/{eventId}/incidents
```

Potential contents:

```text
goals
cards
substitutions
VAR
match timeline events
```

## Player heatmap

```text
GET /event/{eventId}/player/{playerId}/heatmap
```

Provides x/y heatmap points.

## Average positions

Current community tooling uses:

```text
GET /event/{eventId}/average-positions
```

## Player shot map

Current community references document:

```text
GET /event/{eventId}/shotmap/player/{playerId}
```

Potential shot-level fields include:

```text
coordinates
xG
xGOT where available
shot outcome
shot attributes
```

## Rating breakdown / action stream

Current community references document:

```text
GET /event/{eventId}/player/{playerId}/rating-breakdown
```

This may expose individual actions related to:

```text
passes
dribbles
defensive actions
ball carries
```

This route is worth investigating during collector implementation because it may materially increase the event-level dataset.

## Native IDs

Sofascore exposes strong numeric IDs for:

```text
event
team
player
tournament
season
```

## Collection target

For each fixture, initially collect:

```text
/event/{id}
/event/{id}/statistics
/event/{id}/lineups
/event/{id}/incidents
/event/{id}/average-positions
```

Then, where available and useful:

```text
player heatmaps
player shot maps
rating breakdown / action data
```

## Notes

These are public website endpoints but not a supported developer API.

Community documentation notes bot monitoring / rate limiting.

Do not make unnecessary duplicate requests when one endpoint already contains the same data.


---

# 6. Understat

## Role

Primary shot-level expected-goal source and supplementary player/team attacking source.

Coverage includes the Premier League historically from 2014/15 onward.

## Access

Useful current package:

- https://github.com/collinb9/understatAPI
- https://pypi.org/project/understatapi/

`soccerdata` also supports Understat:

- https://soccerdata.readthedocs.io/en/latest/datasources/Understat.html

## Main source objects

The current Understat API wrapper exposes:

```text
league
team
player
match
```

Conceptual website routes include:

```text
https://understat.com/league/EPL
https://understat.com/team/{team}/{season}
https://understat.com/player/{player_id}
```

## Useful grains

```text
player-season
team-season
player-match
team-match
shot
```

## Player-match data

Current soccerdata support exposes fields including:

```text
league_id
season_id
game_id
team_id
player_id
position
position_id
minutes
goals
own_goals
shots
xg
xa
xg_chain
xg_buildup
```

## Shot data

Collect every available shot record.

Important fields include concepts such as:

```text
match
player
team
minute
x
y
xG
result
situation
shot type
key-pass / assisting player
```

## Native IDs

Understat exposes IDs for:

```text
league
season
game
team
player
```

## Collection target

Collect:

```text
league player data
league/team match data
player match data
all shot events
```

Do not reduce Understat to season-level xG totals; the shot-level records are much more valuable.


---

# 7. PremierLeague.com Stats Centre

## Role

Official Premier League statistical source.

Primary use:

```text
player season totals
club season totals
official cross-checks
metrics not exposed elsewhere
```

## Access

Current Stats Centre:

- https://www.premierleague.com/en/stats/

Examples:

```text
https://www.premierleague.com/en/stats/top/players/expected-goals
https://www.premierleague.com/en/stats/top/players/through-balls
https://www.premierleague.com/en/stats/top/clubs
```

## Current observed metric families

The Stats Centre currently exposes player/team categories covering areas such as:

```text
goals
assists
appearances
minutes
cards
passes
touches
shots
expected goals
clean sheets
defensive statistics
passing statistics
```

Availability varies by season and metric.

The site notes that some statistics are not available before 2006/07.

## Grain

Primarily:

```text
player-season
team-season
```

Potentially other filtered views depending on site implementation.

## Identity

Player and club pages / site objects should be inspected during implementation to determine the most useful persistent source identifiers.

If stable site IDs are available in the underlying page/API response, retain them.

Otherwise resolution through:

```text
player name
club
season
```

is feasible.

## Collection target

Scrape every available current-season player and club stat table that can be resolved cleanly.

This source is especially useful as an official aggregate reference during reconciliation.


---

# 8. StatBunker

## Role

Broad free statistical-table source.

Current Premier League pages expose a large catalogue covering:

```text
players
clubs
goals
assists
discipline
appearances
clean sheets
penalties
shots
injuries / suspensions
referees
fantasy statistics
results
fixtures
```

## Access

Base site:

- https://www.statbunker.com/

The 2026/27 Premier League currently uses a competition identifier in URLs, e.g.:

```text
comp_id=791
```

Example pages:

- https://www.statbunker.com/competitions/LeagueTable?comp_id=791
- https://www.statbunker.com/competitions/FantasyFootballPlayersStats?comp_id=791
- https://www.statbunker.com/competitions/InjuriesAndSuspensions?comp_id=791

## Grain

Mostly:

```text
competition-season
player-season
team-season
fixture
```

Some pages may expose narrower subsets or per-match records through navigation.

## Identity

Competition IDs are explicit.

Player/team identities should be extracted from page links if stable IDs are present; otherwise resolve through:

```text
name
team
competition
season
```

## Collection target

Because StatBunker has many separate statistic views, it is best treated as a page catalogue.

Once a collector exists:

1. discover every Premier League statistic page
2. parse all tables
3. retain source page / metric identity
4. resolve rows to player/team/fixture keys
5. use its broad coverage as both supplementary data and reconciliation evidence

## Note

StatBunker advertises a commercial feed, but the website statistical tables themselves are freely visible and are the relevant source for this project.


---

# 9. Football-Data.co.uk

## Role

Simple, long-running downloadable match-level source.

Best for:

```text
results
half-time results
traditional team match stats
odds
historical backfill
```

## Access

Main downloads:

- https://www.football-data.co.uk/downloadm.php
- https://www.football-data.co.uk/englandm.php

Current-season Premier League CSV files are available.

Historical season ZIP/CSV files extend back many seasons; the overall archive currently goes back to 1993/94 for supported competitions.

## Grain

```text
fixture
fixture + team
```

No meaningful player layer.

## Typical fields

Depending on season:

```text
date
time
home team
away team
full-time score
half-time score
shots
shots on target
fouls
corners
cards
odds
```

## Identity

No strong canonical player concern.

Fixtures can be resolved through:

```text
home team
away team
date / kickoff
competition-season
```

## Collection target

Download the full Premier League CSV for every desired season.

This is low-cost to ingest and useful for historical fixture coverage and reconciliation.


---

# 10. Transfermarkt

## Role

Primary supplementary source for:

```text
squads
player metadata
positions
transfers
loans
injuries
suspensions
availability
market values
```

Not primarily a football event-statistics source.

## Access

Competition code for the Premier League:

```text
GB1
```

Useful page families include:

### Competition

```text
https://www.transfermarkt.co.uk/wettbewerb/startseite/wettbewerb/GB1
```

### Transfers by season

```text
https://www.transfermarkt.co.uk/premier-league/transfers/wettbewerb/GB1/saison_id/{YEAR}
```

Example:

```text
saison_id/2026
```

### Injuries

```text
https://www.transfermarkt.co.uk/premier-league/verletztespieler/wettbewerb/GB1/
```

### Suspensions / absences

Page family:

```text
/sperrenausfaelle/wettbewerb/GB1
```

## Useful grains

```text
player
team
player + team + date
transfer
injury spell
suspension spell
season
```

## Native IDs

Transfermarkt player and club links generally embed persistent site IDs in URLs.

These should be extracted and stored rather than relying only on names.

## Collection target

Collect:

```text
competition club list
team squads
player profile basics
transfers
loans
injuries
suspensions
return / expected-return dates where shown
```

Historical transfer data is particularly useful for reconstructing team membership over time.


---

# 11. ClubElo

## Role

Historical team-strength source.

## Access

ClubElo provides a free CSV API:

```text
http://api.clubelo.com/
```

Current soccerdata documentation confirms this route.

Useful patterns:

### All clubs on a date

```text
http://api.clubelo.com/YYYY-MM-DD
```

### Full history for one club

```text
http://api.clubelo.com/{ClubApiName}
```

Examples of API-style club names include forms such as:

```text
ManCity
Liverpool
```

## Grain

```text
team + date
```

## Useful fields

Current tooling exposes concepts including:

```text
club
country
level
rank
elo
date / validity period
```

## Identity

ClubElo's club API name acts as the source key.

Map once to canonical `t_id`.

## Collection target

For Premier League clubs:

```text
full club history
```

or alternatively daily snapshots.

Full team histories are probably simpler for historical model construction.


---

# 12. FBref — Conditional

## Current position

Do not treat FBref as the primary current-season advanced-stat source.

Current 2026/27 pages exist and standard data remains useful, but many advanced passing fields that previously made FBref exceptionally valuable are currently blank.

Examples observed in current pages:

```text
standard team/player data populated
playing-time data populated
some passing-table columns / advanced fields blank
```

## Access

Current Premier League base:

- https://fbref.com/en/comps/9/2026-2027/

Current examples:

- https://fbref.com/en/comps/9/passing/Premier-League-Stats
- https://fbref.com/en/comps/9/passing_types/Premier-League-Stats
- https://fbref.com/en/comps/9/2026-2027/playingtime/2026-2027-Premier-League-Stats

`soccerdata` can scrape FBref, but current availability of individual columns should be checked rather than assumed.

## Use

Collect opportunistically where populated, particularly:

```text
standard stats
playing time
historical seasons
```

Do not make current advanced metrics a hard dependency.


---

# 13. Squawka — Conditional Investigation

## Why it is interesting

The current Squawka 2026/27 Premier League stats page advertises:

```text
90+ player metrics
90+ team metrics
```

across areas including:

```text
shooting
passing
duels
defending
discipline
goalkeeping
```

Current page:

- https://www.squawka.com/en/stats/competitions/premier-league-2026-2027/

## Grain

Likely primarily:

```text
player-season
team-season
```

## Action

Inspect the site's underlying requests before implementing a collector.

If the tables are backed by structured requests with stable player/team identities, this is potentially a high-value supplementary source.

Do not depend on it until the extraction mechanism and identifiers have been confirmed.


---

# 14. Other Sources to Treat as Low Priority

## Yahoo Sports

Current Premier League statistics pages expose basic player passing/shooting leaderboards.

Potentially useful as another reconciliation source, but coverage appears narrower than the primary sources.

## Generic score/news sites

Sites that expose only:

```text
scores
basic scorers
league tables
```

add little once FotMob, Sofascore, Football-Data and the official PL source are collected.

Do not spend collector effort on them unless they expose a metric absent elsewhere.


---

# 15. Recommended Initial Collector Order

Implementation order:

```text
1. FotMob
2. Sofascore
3. Understat
4. WhoScored
5. PremierLeague.com
6. StatBunker
7. Football-Data.co.uk
8. Transfermarkt
9. ClubElo
10. FBref opportunistically
11. Squawka investigation
```

Rationale is operational:

- start with structured JSON sources
- add shot-level data
- then add the browser-dependent event stream
- then aggregate / validation sources
- then contextual sources


---

# 16. Minimum Raw Capture Per Source

Regardless of final staging schema, every collector should retain enough source context to reconstruct identity.

At minimum where available:

```text
source
source competition ID
source season ID
source fixture ID
source team ID
source player ID
source event ID

source names
fixture date / kickoff
home / away identity

raw payload / source table row
retrieval timestamp
```

Not every source exposes every identifier.

The rule is simply to preserve all source identity information that exists.


---

# 17. Maximum-Data Rule

When an endpoint or page contains additional structured fields:

> collect them unless there is a concrete reason not to.

Examples of fields that should not be discarded just because they are not part of the first model:

```text
shirt number
formation
average position
touch coordinates
qualifiers
referee
venue
captaincy
market value
injury reason
transfer type
shot body part
goal mouth coordinates
period-specific team stats
provider aggregate totals
```

Model usefulness is a downstream decision.


---

# 18. Aggregate and Event Data Should Both Be Collected

If a provider exposes:

```text
individual pass events
```

and separately:

```text
player total passes
```

collect both.

The aggregate can later be used to:

```text
validate event parsing
detect missing events
understand provider definitions
support reconciliation
```

The fact that an aggregate can theoretically be rebuilt does not make the provider aggregate useless.


---

# 19. Current Reference Links

## General multi-source scraper

- https://github.com/probberechts/soccerdata
- https://soccerdata.readthedocs.io/

## WhoScored

- https://www.whoscored.com/
- https://github.com/probberechts/soccerdata/blob/master/soccerdata/whoscored.py

## FotMob

- https://www.fotmob.com/
- https://github.com/ccdejene/fotmob-mcp/blob/main/docs/fotmob-api.md

## Sofascore

- https://www.sofascore.com/
- https://api.sofascore.com/api/v1
- https://github.com/Tariq-15/TacosScore/blob/main/docs/sofascore-api-reference.md
- https://github.com/federicorabanos/LanusStats/blob/main/LanusStats/sofascore.py

## Understat

- https://understat.com/
- https://github.com/collinb9/understatAPI
- https://soccerdata.readthedocs.io/en/latest/datasources/Understat.html

## Premier League Stats Centre

- https://www.premierleague.com/en/stats/

## StatBunker

- https://www.statbunker.com/

## Football-Data.co.uk

- https://www.football-data.co.uk/downloadm.php
- https://www.football-data.co.uk/englandm.php

## Transfermarkt

- https://www.transfermarkt.co.uk/wettbewerb/startseite/wettbewerb/GB1

## ClubElo

- http://clubelo.com/
- http://api.clubelo.com/

## FBref

- https://fbref.com/en/comps/9/

## Squawka

- https://www.squawka.com/en/stats/competitions/premier-league-2026-2027/
