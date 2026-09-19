# Exploratory Data Audit

Source: `C:\Users\SUJAY DAS\Desktop\here-s-a-detailed-brief-you\data\raw\transfermarkt-datasets.duckdb`

## Table row counts and date ranges

| Table | Rows | Date column | Minimum | Maximum |
|---|---:|---|---|---|
| players | 50149 | date_of_birth | 1968-07-31 00:00:00 | 2011-02-23 00:00:00 |
|  |  | contract_expiration_date | 2000-05-31 00:00:00 | 2035-06-30 00:00:00 |
| appearances | 1894350 | date | 2012-07-03 | 2026-06-28 |
| games | 88958 | date | 2006-06-09 | 2026-07-06 |
| competitions | 65 | - | - | - |
| player_valuations | 656301 | date | 2000-01-20 | 2026-06-12 |

## Null percentages

| Table | Column | Type | Null rows | Null % |
|---|---|---|---:|---:|
| players | player_id | INTEGER | 0 | 0.0000% |
| players | first_name | VARCHAR | 3,164 | 6.3092% |
| players | last_name | VARCHAR | 0 | 0.0000% |
| players | name | VARCHAR | 0 | 0.0000% |
| players | last_season | VARCHAR | 0 | 0.0000% |
| players | current_club_id | VARCHAR | 0 | 0.0000% |
| players | player_code | VARCHAR | 0 | 0.0000% |
| players | country_of_birth | VARCHAR | 5,885 | 11.7350% |
| players | city_of_birth | VARCHAR | 5,608 | 11.1827% |
| players | country_of_citizenship | VARCHAR | 269 | 0.5364% |
| players | date_of_birth | TIMESTAMP | 49 | 0.0977% |
| players | sub_position | VARCHAR | 586 | 1.1685% |
| players | position | VARCHAR | 0 | 0.0000% |
| players | foot | VARCHAR | 5,893 | 11.7510% |
| players | height_in_cm | INTEGER | 4,365 | 8.7041% |
| players | contract_expiration_date | TIMESTAMP | 18,569 | 37.0277% |
| players | agent_name | VARCHAR | 23,296 | 46.4536% |
| players | image_url | VARCHAR | 0 | 0.0000% |
| players | international_caps | INTEGER | 30,793 | 61.4030% |
| players | international_goals | INTEGER | 30,793 | 61.4030% |
| players | current_national_team_id | VARCHAR | 46,889 | 93.4994% |
| players | url | VARCHAR | 0 | 0.0000% |
| players | current_club_domestic_competition_id | VARCHAR | 2,986 | 5.9543% |
| players | current_club_name | VARCHAR | 2,986 | 5.9543% |
| players | market_value_in_eur | INTEGER | 8,621 | 17.1908% |
| players | highest_market_value_in_eur | INTEGER | 8,621 | 17.1908% |
| appearances | appearance_id | VARCHAR | 0 | 0.0000% |
| appearances | game_id | INTEGER | 0 | 0.0000% |
| appearances | player_id | INTEGER | 0 | 0.0000% |
| appearances | player_club_id | INTEGER | 0 | 0.0000% |
| appearances | player_current_club_id | VARCHAR | 0 | 0.0000% |
| appearances | date | DATE | 0 | 0.0000% |
| appearances | player_name | VARCHAR | 2 | 0.0001% |
| appearances | competition_id | VARCHAR | 0 | 0.0000% |
| appearances | yellow_cards | INTEGER | 0 | 0.0000% |
| appearances | red_cards | INTEGER | 0 | 0.0000% |
| appearances | goals | INTEGER | 0 | 0.0000% |
| appearances | assists | INTEGER | 0 | 0.0000% |
| appearances | minutes_played | INTEGER | 0 | 0.0000% |
| games | game_id | VARCHAR | 0 | 0.0000% |
| games | competition_id | VARCHAR | 0 | 0.0000% |
| games | season | VARCHAR | 0 | 0.0000% |
| games | round | VARCHAR | 0 | 0.0000% |
| games | date | DATE | 0 | 0.0000% |
| games | home_club_id | INTEGER | 0 | 0.0000% |
| games | away_club_id | INTEGER | 0 | 0.0000% |
| games | home_club_goals | INTEGER | 0 | 0.0000% |
| games | away_club_goals | INTEGER | 0 | 0.0000% |
| games | home_club_position | INTEGER | 25,377 | 28.5269% |
| games | away_club_position | INTEGER | 25,377 | 28.5269% |
| games | home_club_manager_name | VARCHAR | 844 | 0.9488% |
| games | away_club_manager_name | VARCHAR | 844 | 0.9488% |
| games | stadium | VARCHAR | 242 | 0.2720% |
| games | attendance | INTEGER | 10,803 | 12.1439% |
| games | referee | VARCHAR | 678 | 0.7622% |
| games | url | VARCHAR | 0 | 0.0000% |
| games | home_club_formation | VARCHAR | 8,200 | 9.2178% |
| games | away_club_formation | VARCHAR | 8,073 | 9.0751% |
| games | home_club_name | VARCHAR | 86 | 0.0967% |
| games | away_club_name | VARCHAR | 36 | 0.0405% |
| games | aggregate | VARCHAR | 0 | 0.0000% |
| games | competition_type | VARCHAR | 1,214 | 1.3647% |
| competitions | competition_id | VARCHAR | 0 | 0.0000% |
| competitions | competition_code | VARCHAR | 0 | 0.0000% |
| competitions | name | VARCHAR | 0 | 0.0000% |
| competitions | sub_type | VARCHAR | 0 | 0.0000% |
| competitions | type | VARCHAR | 0 | 0.0000% |
| competitions | country_id | INTEGER | 0 | 0.0000% |
| competitions | country_name | VARCHAR | 12 | 18.4615% |
| competitions | domestic_league_code | VARCHAR | 12 | 18.4615% |
| competitions | confederation | VARCHAR | 0 | 0.0000% |
| competitions | total_clubs | INTEGER | 15 | 23.0769% |
| competitions | url | VARCHAR | 0 | 0.0000% |
| player_valuations | player_id | INTEGER | 0 | 0.0000% |
| player_valuations | date | DATE | 0 | 0.0000% |
| player_valuations | market_value_in_eur | INTEGER | 0 | 0.0000% |
| player_valuations | current_club_name | VARCHAR | 0 | 0.0000% |
| player_valuations | current_club_id | INTEGER | 0 | 0.0000% |
| player_valuations | player_club_domestic_competition_id | VARCHAR | 92,973 | 14.1662% |

## Join coverage

| Check | Source rows | Matched rows | Unmatched rows | Match % |
|---|---:|---:|---:|---:|
| appearances_player | 1,894,350 | 1,894,348 | 2 | 99.9999% |
| appearances_game | 1,894,350 | 1,894,350 | 0 | 100.0000% |
| appearances_competition | 1,894,350 | 1,880,150 | 14,200 | 99.2504% |
| valuations_player | 656,301 | 656,301 | 0 | 100.0000% |
| valuations_positive_value | 656,301 | 656,300 | 1 | 99.9998% |

## Duplicate key groups

| Check | Groups |
|---|---:|
| players_duplicate_player_ids | 0 |
| games_duplicate_game_ids | 0 |
| valuations_duplicate_player_date | 0 |

## Valuation distribution (EUR)

| Rows | Null values | Minimum | P01 | P25 | Median | P75 | P99 | Maximum | Mean |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 656,301 | 0 | 0 | 25,000.0000 | 200,000.0000 | 500,000.0000 | 1,500,000.0000 | 32,000,000.0000 | 200,000,000 | 2,290,092.7440 |

## Game rows by season

| Season | Game rows |
|---|---:|
| 2005 | 64 |
| 2007 | 31 |
| 2009 | 64 |
| 2011 | 31 |
| 2012 | 5,700 |
| 2013 | 5,826 |
| 2014 | 5,836 |
| 2015 | 5,759 |
| 2016 | 5,699 |
| 2017 | 5,660 |
| 2018 | 5,723 |
| 2019 | 5,469 |
| 2020 | 5,564 |
| 2021 | 5,939 |
| 2022 | 6,008 |
| 2023 | 5,951 |
| 2024 | 10,036 |
| 2025 | 9,598 |

## Valuation rows by year

| Year | Valuation rows |
|---:|---:|
| 2000 | 1 |
| 2001 | 1 |
| 2003 | 2 |
| 2004 | 2,305 |
| 2005 | 2,439 |
| 2006 | 2,673 |
| 2007 | 5,617 |
| 2008 | 9,305 |
| 2009 | 12,067 |
| 2010 | 13,795 |
| 2011 | 17,788 |
| 2012 | 19,714 |
| 2013 | 22,636 |
| 2014 | 23,707 |
| 2015 | 30,479 |
| 2016 | 34,653 |
| 2017 | 35,923 |
| 2018 | 41,097 |
| 2019 | 46,088 |
| 2020 | 48,749 |
| 2021 | 58,412 |
| 2022 | 59,564 |
| 2023 | 57,576 |
| 2024 | 45,376 |
| 2025 | 45,482 |
| 2026 | 20,852 |
