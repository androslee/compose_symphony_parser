import datetime
import time
import typing

import requests
import edn_format
import pandas as pd
import pytz

from . import edn_syntax


UTC_TIMEZONE = pytz.UTC


def epoch_days_to_date(days: int) -> datetime.date:
    # if your offset is negative, this will fix the off-by-one error
    # if your offset is positive, you'll never know this problem even exists
    return datetime.datetime.fromtimestamp(days * 24 * 60 * 60, tz=UTC_TIMEZONE).date()


def date_to_epoch_days(day: datetime.date) -> int:
    return int(datetime.datetime.combine(day, datetime.time(
        0, 0), tzinfo=UTC_TIMEZONE).timestamp() / 60 / 60 / 24)


assert epoch_days_to_date(19289) == datetime.date(2022, 10, 24)


def get_composer_backtest_results(symphony_id: str, start_date: datetime.date) -> dict:
    epoch_days = date_to_epoch_days(start_date)
    utc_today = datetime.datetime.now().astimezone(UTC_TIMEZONE).date()

    payload = "{:uid nil, :start-date-in-epoch-days START_DATE_EPOCH_DAYS, :capital 10000, :apply-taf-fee? true, :symphony-benchmarks [], :slippage-percent 0.0005, :apply-reg-fee? true, :symphony \"SYMPHONY_ID_GOES_HERE\", :ticker-benchmarks []}"
    payload = payload.replace("SYMPHONY_ID_GOES_HERE", symphony_id)
    payload = payload.replace("START_DATE_EPOCH_DAYS", str(epoch_days))

    print(
        f"Fetching backtest results for {symphony_id} from {start_date} to {utc_today}...")

    tries_remaining = 3
    response = None
    while tries_remaining:
        try:
            response = requests.post(
                "https://backtest.composer.trade/v2/backtest",
                json=payload)
            response.raise_for_status()
            break
        except requests.HTTPError as e:
            time.sleep(3)
            print("Error when submitting backtest:", e)
            tries_remaining -= 1

    if not response:
        raise Exception("Failed to submit backtest after retries")

    backtest_result = edn_syntax.convert_edn_to_pythonic(
        edn_format.loads(response.text))

    return typing.cast(dict, backtest_result)


def extract_allocations_from_composer_backtest_result(backtest_result: dict) -> pd.DataFrame:
    composer_allocations = pd.DataFrame(
        backtest_result[':tdvm-weights']).fillna(0).round(4)
    composer_allocations.index = pd.DatetimeIndex(
        [epoch_days_to_date(i) for i in composer_allocations.index])
    composer_allocations.sort_index(inplace=True)
    return composer_allocations.round(4)


def extract_returns_from_composer_backtest_result(backtest_result: dict, symphony_id: str) -> pd.Series:
    dvm_capital = backtest_result[':dvm-capital'][symphony_id]
    returns_by_day = sorted([
        (pd.to_datetime(epoch_days_to_date(k)), v) for k, v in dvm_capital.items()
    ])
    returns = pd.Series([row[1] for row in returns_by_day], index=[
                        row[0] for row in returns_by_day]).pct_change().dropna()
    return returns
