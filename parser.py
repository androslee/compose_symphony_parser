#! /usr/bin/python3


'''

lets build a text parser that reads in a raw symphony payload, and can export it to whatever endpoint we like
human readable output
quantconnect
vectorbt
tradingview
thinkscript


'''
import string
import edn_format
import argparse
import json
import sys
import requests
import re


class InFileReader:
    
    def __init__(self, filePath :string, fileData :string):
        self.filePath = filePath
        self.file_contents_string = fileData
        self.data = None
        return
        
        
    def readFile(self):
        if self.file_contents_string == None:
            with open(self.filePath, "r") as infile:
                self.file_contents_string = infile.read()
        #  'inputFile.edn'
            data_with_wrapping_string_removed = json.load(self.file_contents_string)
            self.data = edn_format.loads(data_with_wrapping_string_removed)
        else:
            self.data = edn_format.loads(self.file_contents_string)
        #>>> edn_format.dumps({1, 2, 3})
        #'#{1 2 3}'
        
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
        
    
#TODO finish    
class OutfileVectorBt(OutfileBase):
    
    
    def __init__(self):
        super().__init__()
        return
        
    # 
    def show(self, data):
        for key in data:
            print(data[key])
            
        print("\r\n this shows the data ends up being nested dictionaries.  further parsing/looping is needed")
        

#TODO arg parser for inputs: input file, output file, output mode
def main()-> int:
    parser = argparse.ArgumentParser(description='Composer Symphony text parser')
    parser.add_argument('-i','--infile', dest="infile", action="store", help=' input file we read the symphony text from.  full path please', required=True)
    parser.add_argument('-u', '--url', action="store_true", help="specifies that the input file path is actually the url to a shared, public symphony on composer.trade")
    parser.add_argument('-o','--outfile', dest="outfile", action="store", default="OUTFILE", help=' output file to save the parsed text to.  if not given, will use stdout', required=False)
    parser.add_argument('-m','--mode', dest="mode", action="store", default="human", help=' output parsing mode to use.  if none given, will parse for "human readable output".  modes are: quantconnect, vectorbt, tradingview, thinkscript', required=False)
    args = vars(parser.parse_args())

    if args['url'] == True:
        #todo move to request this from the composer site instead of hardcoding
        composerConfig = {
                "projectId" : "leverheads-278521",
                "databaseName" : "(default)"
            }
        m = re.search('\/symphony\/([^\/]+)', args["infile"])
        symphId = m.groups(1)[0]
        symphReq = requests.get(f'https://firestore.googleapis.com/v1/projects/{composerConfig["projectId"]}/databases/{composerConfig["databaseName"]}/documents/symphony/{symphId}')
        resp = json.loads(symphReq.text)
  
        inFileParser = InFileReader(None, resp['fields']['latest_version_edn']['stringValue'])
    else:
        print(args["infile"])
        inFileParser = InFileReader(args["infile"], None)
    
    inFileParser.readFile()
    
    
    
    if args["mode"] == "human":
        humanParser = OutfileHuman(args["infile"])
        humanParser.show(inFileParser.file_contents_string)
    
    if args["mode"] == "vector":
        vectorParser = OutfileVectorBt()
        vectorParser.show(inFileParser.data)
    
    return 0
#TODO make generic class for output mode



#TODO make child classes for specific output modes


#TODO start listing out initial requirements for each specific output mode


if __name__ == '__main__':
    sys.exit(main()) 