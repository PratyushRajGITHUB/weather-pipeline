-- 1. View all weather records
SELECT *
FROM `striped-buckeye-512500-d1.global_weather_data.current_weather_stats`;

-- 2. Check the total number of cities
SELECT COUNT(*) AS total_cities
FROM `striped-buckeye-512500-d1.global_weather_data.current_weather_stats`;

-- 3. Check for missing values
SELECT
COUNTIF(City IS NULL) AS missing_city,
COUNTIF(Country IS NULL) AS missing_country,
COUNTIF(Population IS NULL) AS missing_population,
COUNTIF(Temperature IS NULL) AS missing_temperature,
COUNTIF(Wind_Speed IS NULL) AS missing_wind_speed
FROM `striped-buckeye-512500-d1.global_weather_data.current_weather_stats`;

-- 4. Find the five hottest cities with a city population above 10 million
SELECT
City,
Country,
Population,
Temperature,
Temperature_Fahrenheit,
Temperature_Category
FROM `striped-buckeye-512500-d1.global_weather_data.current_weather_stats`
WHERE Population > 10000000
ORDER BY Temperature DESC
LIMIT 5;

-- 5. Create a view of the five hottest qualifying cities
CREATE OR REPLACE VIEW
`striped-buckeye-512500-d1.global_weather_data.vw_hottest_large_countries` AS
SELECT
City,
Country,
Population,
Temperature,
Temperature_Fahrenheit,
Temperature_Category
FROM `striped-buckeye-512500-d1.global_weather_data.current_weather_stats`
WHERE Population > 10000000
ORDER BY Temperature DESC
LIMIT 5;
