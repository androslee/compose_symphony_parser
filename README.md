# compose_symphony_parser
a text parser that will attempt to export a text encoded composer symphony, to whatever text endpoint you want



- human readable output
- quantconnect
- vectorbt
- tradingview
- thinkscript

usages:

parser.py -i infile -o outfile -m quantconnect
	saves quantconnect parsed output to "outfile"
	
parser.py -i infile 
	will just print human readable output to the screen

infile: the file that contains the text encoded symphony 
outfile: the file you want the parsed output to go to
quantconnect: the output mode style
	eventual, hopeful, supported output style modes: quantconnect, vectorbt, tradingview, thinkscript

in order for an output style to be supported, it does not have to be 100% complete.  it can only be 10% complete to be supported.  as long as it helps someone convert the original text, and get them closer from the original encoded text, to the "Other" system, then its a nice, good conversion.