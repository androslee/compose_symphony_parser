# compose_symphony_parser
a text parser that will attempt to export a text encoded composer symphony, to whatever text endpoint you want

- [x] human readable output
- [ ] vectorbt (WIP)
- [x] quantconnect (using ChatGPT)
- [ ] tradingview
- [ ] thinkscript

# Requirements

Use python3.

```bash
pip3 install -r requirements.txt
```

## ChatGPT Transpiling Support

Support for QuantConnect strategies is done by leveraging ChatGPT to transpile the human-readable format into a QuantConnect strategy.
`python3 ./parser.py -m quantconnect -i https://app.composer.trade/symphony/PdgUAAy4GmEQvGyKsYZt/details -u`

You must have ChatGPT / OpenAI credential (https://chat.openai.com/chat) and place them in the `lib/quantconnect.py` at the top like so:
```python
	config = {
		"email": "your@email.address",
		"password": "password"
	}
```

# Usage
```
python3 symphony_parser.py -i infile -o outfile -m quantconnect
	saves quantconnect parsed output to "outfile" (NOT TESTED, MAY NOT WORK)

python3 symphony_parser.py -i inputs/simple.edn -m vector
  prints vectorbt output to screen

python3 symphony_parser.py -i infile 
	will just print human readable output to the screen
	
 python3 symphony_parser.py -m vector -i https://app.composer.trade/symphony/PdgUAAy4GmEQvGyKsYZt/details -u
  will print a vectorbt formatted output, will download a symphony directly from composer

python3 symphony_parser.py -m human -u -i https://app.composer.trade/symphony/PdgUAAy4GmEQvGyKsYZt/details -p
  prints a human formatted output, download the json formatted edn_encoded symphony directly from composer, AND all symphony parents, printing them directly to the screen

python3 symphony_parser.py -m human -p -u -b -i inputs/bulk_symphonies.txt 
 prints a human formatted output, download the json formatted edn_encoded symphony directly from composer, all symphony parents, printing them directly to the screen, AND reads the text file which contains a list of urls which it bulk reads from.  can be urls or a list of local file paths for json encoded edn files.

python3 .ymphony_parser.py -m quantconnect -i https://app.composer.trade/symphony/PdgUAAy4GmEQvGyKsYZt/details -u
  will print a C# QuantConnect strategy, transpiled by ChatGPT

infile: the file that contains the text encoded symphony 

	you can now use the -u option when specifying an infile. This will cause it to treat the infile as a symphony url and it will then pull the data down from composer. 

outfile: the file you want the parsed output to go to
quantconnect: the output mode style
	eventual, hopeful, supported output style modes: quantconnect, vectorbt, tradingview, thinkscript
```

In order for an output style to be supported, it does not have to be 100% complete.  it can only be 10% complete to be supported.  as long as it helps someone convert the original text, and get them closer from the original encoded text, to the "Other" system, then its a nice, good conversion.

to get the backtesting syntax:

"in your composer page, before you change a date on the backtesting graph, and cause the webpage to do another backtest, have the inspect tool open, and on the network tab, so it's monitoring your network traffic.  change the date.  this will send a request to the backend.  as it's monitoring your networking graph, it will endcode the symphony on the page in text, and you should be able to find it in one of those."


sample composer syntax as of 10-18
```edn
 [{:id \"a6cea29d-15a3-48d6-900a-e8570fdef804\", :step :wt-cash-equal, :children [{:id \"d4ece5ac-9a5f-4f50-86ee-f2ca82a5b31e\", :step :if, :children [{:children [{:id \"4fcf1c2a-e747-413f-b3b3-75c6004c791b\", :step :wt-cash-equal, :children [{:id \"4a465370-bd84-493a-b4e1-cedc27e00cae\", :step :if, :children [{:children [{:id \"c7303d3f-3a51-422f-ac91-9b349ab798a0\", :step :group, :name \"Overbought S&P. Sell the rip. Buy volatility\", :children [{:step :wt-cash-equal, :id \"5b7f5cdf-4611-4aa2-b277-e03b1fc87a70\", :children [{:select? true, :children [{:name \"ProShares Ultra VIX Short-Term Futures ETF\", :ticker \"UVXY\", :has_marketcap false, :id \"c82bef09-9dd6-498f-aa54-b1920bd52fed\", :exchange \"BATS\", :price 11.45, :step :asset, :dollar_volume 453424499.84999996} {:name \"ProShares VIX Short-Term Futures ETF\", :ticker \"VIXY\", :has_marketcap false, :id \"57f4b706-3cca-4e06-895e-7f435bae9c3a\", :exchange \"BATS\", :price 15.84, :step :asset, :dollar_volume 149119153.92}], :select-fn :bottom, :select-n \"1\", :sort-by-fn :relative-strength-index, :sort-by-window-days \"13\", :weight {:num \"80\", :den 100}, :id \"d74aeaea-5b9d-44b5-a0eb-61c60d9532e8\", :sort-by? true, :collapsed-specified-weight? false, :step :filter}]}], :collapsed? false}], :is-else-condition? false, :rhs-fixed-value? true, :lhs-fn :relative-strength-index, :lhs-window-days \"7\", :lhs-val \"SPY\", :id \"0cb24ab6-f9b2-4a6a-9a14-9a87d9839400\", :comparator :gt, :rhs-val \"76\", :step :if-child} {:id \"9d8b558a-0a21-48e4-952c-b1014ba700cd\", :step :if-child, :is-else-condition? true, :children [{:id \"3698f968-4859-45db-8a2d-83d332e41141\", :step :wt-cash-equal, :children [{:name \"Direxion Daily Semiconductor Bull 3x Shares\", :ticker \"SOXL\", :has_marketcap false, :id \"3bd5e2c3-ef00-463d-8eb5-f88fb765460d\", :exchange \"ARCX\", :price 11.19, :step :asset, :dollar_volume 1275587444.04}]}]}]}]}], :rhs-fn :relative-strength-index, :is-else-condition? false, :rhs-fixed-value? false, :lhs-fn :relative-strength-index, :rhs-window-days \"5\", :lhs-window-days \"5\", :lhs-val \"BIL\", :id \"9da13422-9cb9-4b01-a3be-64edff9d95e3\", :comparator :lt, :rhs-val \"BND\", :step :if-child} {:id \"03f583d0-5608-4618-ba12-c3dff9db75fb\", :step :if-child, :is-else-condition? true, :children [{:id \"7902f025-3e45-4d12-9722-3a587b006e5d\", :step :wt-cash-equal, :children [{:id \"91c6e86e-cafd-4547-b371-b0adc0647062\", :step :if, :children [{:children [{:id \"1a18804f-596c-4979-b968-59862f10eb57\", :step :group, :name \"Extremely oversold S&P (low RSI). Double check with bond mkt before going long\", :children [{:step :wt-cash-equal, :id \"0edc12db-a440-4edb-8f23-84d4979434ac\", :children [{:id \"4e49579c-4407-4ae7-ae74-8eeb1f86d536\", :step :if, :children [{:children [{:name \"Direxion Daily Semiconductor Bear 3x Shares\", :ticker \"SOXS\", :has_marketcap false, :id \"c4f5b6e2-912b-4e6b-8f7c-6a265a1c0799\", :exchange \"ARCX\", :price 53.72, :step :asset, :dollar_volume 871353441.6}], :rhs-fn :relative-strength-index, :is-else-condition? false, :lhs-fn :relative-strength-index, :rhs-window-days \"10\", :lhs-window-days \"10\", :lhs-val \"SHY\", :id \"6fcc22ec-8814-4be5-9cab-afd724c57096\", :comparator :lte, :rhs-val \"HIBL\", :step :if-child} {:id \"93d72d2b-b677-419e-a1f3-d30820a1691c\", :step :if-child, :is-else-condition? true, :children [{:name \"Direxion Daily Semiconductor Bull 3x Shares\", :ticker \"SOXL\", :has_marketcap false, :id \"ef524e04-ef23-473d-a402-bfc070088725\", :exchange \"ARCX\", :price 11.19, :step :asset, :dollar_volume 1275587444.04, :children-count 0}]}]}]}], :collapsed? false}], :is-else-condition? false, :rhs-fixed-value? true, :lhs-fn :relative-strength-index, :lhs-window-days \"7\", :lhs-val \"SPY\", :id \"3e9c24d0-5a75-47c5-ae3a-59aade04e5d4\", :comparator :lt, :rhs-val \"27\", :step :if-child} {:id \"aca26a7c-582e-4d90-9a30-16c01f15f38e\", :step :if-child, :is-else-condition? true, :children [{:id \"66224477-e983-4217-bea1-8a2ca8f221d1\", :step :wt-cash-equal, :children [{:select? true, :children [{:name \"Direxion Daily Semiconductor Bear 3x Shares\", :ticker \"SOXS\", :has_marketcap false, :id \"28b17b5d-af5c-4d9e-8b02-0c757734d8c9\", :exchange \"ARCX\", :price 69.73, :step :asset, :dollar_volume 1365590855.67} {:name \"WisdomTree Bloomberg US Dollar Bullish Fund\", :ticker \"USDU\", :has_marketcap false, :id \"a3d73f2a-e7a3-4c86-aacf-d3212c5759fb\", :exchange \"ARCX\", :price 29.98, :step :asset, :dollar_volume 3695124.94, :children-count 0}], :select-fn :bottom, :select-n \"1\", :sort-by-fn :relative-strength-index, :sort-by-window-days \"7\", :id \"36a95a02-701f-4dc0-91a7-2d4f205b544e\", :sort-by? true, :step :filter}]}]}]}]}]}]}], :window-days \"3\"}]}, :ticker-benchmarks [{:color \"#F6609F\", :id \"SPY\", :checked? true, :type :ticker, :ticker \"SPY\"}]}"
```

it's the EDN-format!!!

https://github.com/edn-format/edn


# TODO:
- compare changes from parent/child
	- difflib.unified_diff
	- print said/show changes
- add line numbers to printed symphonys for easier discussion