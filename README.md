# power-graphing
Visualizing electricity usage through Nest, Weather Underground, and Salt River Project


### Sample Output

![sample graph](/screenshots/graph.png?raw=true "Sample Graph")

### Usage
1. clone this repo
2. acquire a Nest API key, and exchange for a bearer token. Enroll your Nest thermostat to use this API key
3. acquire a Weather Underground API key
4. fill the `secrets.py` file with these values and your zip code
5. run `NestLogger.py` for some time to acquire Nest and Weather Underground data
6. modify the resultant `nest_data.txt` by wrapping in `[` and `]` and removing the final comma, to generate a valid CSV.
7. log in to SRP at https://myaccount.srpnet.com/MyAccount/usage, and export hourly usage values to excel
8. copy it alongside `nest_data.txt` and rename it to `srp_data.csv`
9. run `graph.py`

### Notes
- Much more data is available for analysis: relative humidity, sunlight, indoor ambient, etc...
- Data may misalign if daylight savings time state changes
- Weather Underground tends to favor a single station, it is worth spending time looking at historical data to find the most accurate one

### Todo
- Automatically download SRP's data
- Handle arbitrary SRP data in a directory
- Don't connect graph lines for missing data
- Collect Nest data in local timezone, and specify the timezone in the timestamp

