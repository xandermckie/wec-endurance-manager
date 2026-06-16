## What I'm Building
A browser game where you act as the Team Principal of an FIA World Endurance Championship (WEC)
squad. Objectives are open-ended: chase the title with a star-studded lineup of Platinum-graded
aces, build a youth academy of Bronze and Silver drivers through the Young Driver Programme, or
wheel and deal in the transfer market. There is driver scouting, a budget cap, a transfer/
negotiation engine, full-calendar race simulation, and more.

## Who It's For
For endurance-racing fans who want to run a WEC team in an arcade-like game with no risk to your
job, where you can explore endless what-ifs. Target audience: teenagers and adults who follow
sportscar racing, Le Mans and the WEC.

## The Data
- Name: Curated WEC grid dataset (bundled), no live API required
- What it models: Hypercar and LMGT3 teams, their driver lineups, and a synthetic-but-plausible
  season form for each driver that feeds the rating engine.
- How often it refreshes: rebuilt on demand or daily (locally)
- File format: JSON
- A single driver record looks like:
```json
{
  "id": 101,
  "name": "Kamui Kobayashi",
  "team": "Toyota Gazoo Racing",
  "team_id": 1,
  "ppr": 21.5,
  "pod": 5.0,
  "ovt": 12.0,
  "pol": 3.0,
  "fl": 4.0,
  "gp": 8,
  "overall": 91.0,
  "age": 38,
  "grade": "Platinum"
}
```
Stat keys: ppr = points per round, pod = podiums, ovt = positions gained, pol = poles,
fl = fastest laps.

## User Interactions
- View their squad (driver names, rating, age, grade, contract)
- Driver market (sign free agents)
- Transfer engine (drivers + young-driver test slots, with trade value)
- Race-weekend simulation and live standings

## Error States
- Grid file missing → rebuild from the curated dataset
- Corrupt season save → restore from backup, else start fresh with a disclaimer

## Stretch Goals
- No budget cap mode
- Team-principal personalities (Cheap, Super-Squad Builder, Young Blood, Vet Centric, Balanced)
- AI transfer negotiation
- Difficulty modes
- Driver scouting reports
- Paddock news ticker and media reactions
- Dynamic grid (other teams trading with each other)
