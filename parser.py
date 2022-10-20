#! /usr/bin/python3


'''

lets build a text parser that reads in a raw symphony payload, and can export it to whatever endpoint we like
human readable output
quantconnect
vectorbt
tradingview
thinkscript


'''
import edn_format
import argparse
import json
import sys



class InFileReader:
    
    def __init__(self, filePath):
        self.filePath = filePath
        self.data = None
        return
        
        
    def readFile(self):
        with open(self.filePath, "r") as infile:
            self.data = infile.read()
        #  'inputFile.edn'
        #data_with_wrapping_string_removed = json.load(open(self.filePath, 'r'))
        #self.data = edn_format.loads(data_with_wrapping_string_removed)

        return
        
        


class OutfileBase:
    
    def __init__(self):
    
        return
    
    
    
    
#TODO finish    
class OutfileHuman(OutfileBase):
    
    def __init__(self, filePath):
        super().__init__()
        self.filePath = filePath
        return
    
    def show(self, data):
        data = data.replace(', :', ',:')
        data = data.split(",")
        x = 0
        y = 0
        tabcount = 0
        tabstring = ""
        parsestring = ""

        while x < len(data):

            if "[" in data[x]:
                count = data[x].count("[")
                y = y + count
            if "]" in data[x - 1]:
                count = data[x].count("]")
                y = y - count

            tabstring = "\n"
            while tabcount < y:
                tabstring = tabstring + "  "
                tabcount = tabcount + 1

            tabcount = 0

            data[x] = tabstring + data[x] + ","

            parsestring = parsestring + data[x]

            x = x + 1
        
        print(parsestring)
        return
        
    
    
#TODO finish    
class OutfileQuantConnect(OutfileBase):
    
    
    def __init__(self):
        super().__init__(self)
        return
        
        


#TODO arg parser for inputs: input file, output file, output mode
def main()-> int:
    parser = argparse.ArgumentParser(description='Composer Symphony text parser')
    parser.add_argument('-i','--infile', dest="infile", action="store", help=' input file we read the symphony text from.  full path please', required=True)
    parser.add_argument('-o','--outfile', dest="outfile", action="store", default="OUTFILE", help=' output file to save the parsed text to.  if not given, will use stdout', required=False)
    parser.add_argument('-m','--mode', dest="mode", action="store", default="human", help=' output parsing mode to use.  if none given, will parse for "human readable output".  modes are: quantconnect, vectorbt, tradingview, thinkscript', required=False)
    args = vars(parser.parse_args())

    
    print(args["infile"])
    inFileParser = InFileReader(args["infile"])
    inFileParser.readFile()
    
    humanParser = OutfileHuman(args["infile"])
    
    humanParser.show(inFileParser.data)
    
    return 0
#TODO make generic class for output mode



#TODO make child classes for specific output modes


#TODO start listing out initial requirements for each specific output mode


if __name__ == '__main__':
    sys.exit(main()) 