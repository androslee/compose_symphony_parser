#! /usr/bin/python3


'''

lets build a text parser that reads in a raw symphony payload, and can export it to whatever endpoint we like
human readable output
quantconnect
vectorbt
tradingview
thinkscript


'''
import argparse
import sys



class InFileReader:
    
    def __init__(self, filePath):
        self.filePath = filePath
        return
        
        
    def readFile(self):
        with open(self.filePath, "rb") as infile:
            for line in infile:
                print(line)
        return
        
        


class OutfileBase:
    
    def __init__(self):
    
        return
    
    
    
    
#TODO finish    
class OutfileHuman(OutfileBase):
    
    
    def __init__(self):
        super().__init__(self)
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
    
    
    return 0
#TODO make generic class for output mode



#TODO make child classes for specific output modes


#TODO start listing out initial requirements for each specific output mode


if __name__ == '__main__':
    sys.exit(main()) 