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
import traceback
import requests
import argparse
import random
import typing
import string
import time
import copy
import json
import sys
import re

from lib import edn_syntax, transpilers


class InFileReader:
    
    def __init__(self, filePath :string, resp :dict):
        self.filePath = filePath
        self.resp = resp
        self.data = None
        self.root_node = None
        return
        
        
    def printHeader(self, url_loaded = False):
         # 'latest_backtest_info', 'latest_backtest_edn', 'latest_version', 'hashtag', 'owner', 'description', 'created_at', 'latest_version_edn', 'sparkgraph_url', 'color', 'name', 'share-with-everyone?', 'stats', 'last_updated_at', 'youtube-url', 'cached_rebalance', 'latest_backtest_run_at', 'cached_rebalance_corridor_width', 'copied-from', 'backtest_url'])
        
        if url_loaded:
            
            owner = "UNKNOWN"
            created = "UNKNOWN"
            name = "UNKNOWN"
            description = "UNKNOWN"
            symph_name = "UNKNOWN"
            
            
            if "owner" in self.resp:
                owner = self.resp['owner']
            if "created" in self.resp:
                owner = self.resp['created']
            if "name" in self.resp:
                owner = self.resp['name']
            if "description" in self.resp:
                description = self.resp['description']
            if self.root_node:
                symph_name = self.root_node["name"]
            
            
            print("""\r\n========================================================\r\n
            owner:......... %s\r\n
            creator_name:.. %s\r\n
            created at:.... %s \r\n
            symphony name:. %s\r\n
            description at: %s \r\n
            """ % (owner, name, created, symph_name, description ))
            
            
    def readFile(self, url_loaded = False):
        try:
            # Data is wrapped with "" and has escaped all the "s, this de-escapes
            if not url_loaded:
                data_with_wrapping_string_removed = json.load(
                    open(self.filePath, 'r'))
            else:
                print("I'm fancy and url loaded already\r\n")
                data_with_wrapping_string_removed = self.resp['fields']['latest_version_edn']['stringValue']
            root_data_immutable = edn_format.loads(
                data_with_wrapping_string_removed)
            self.data = typing.cast(
                dict, edn_syntax.convert_edn_to_pythonic(root_data_immutable))
            
            self.root_node = self.data
            if ":symphony" in self.data:
                self.root_node = self.data[":symphony"]
                
        except (NameError, TypeError) as exception_error:
            
            print(exception_error)
            
            my_traceback = traceback.format_exc() # returns a str
            print(my_traceback)
            
            root_data_immutable = edn_format.loads(open(self.filePath, 'r').read())
            self.data = typing.cast(
                dict, edn_syntax.convert_edn_to_pythonic(root_data_immutable))
            
        self.root_node = self.data
        if ":symphony" in self.data:
            self.root_node = self.data[":symphony"]
        '''
        if self.file_contents_string == None:
            with open(self.filePath, "r") as infile:
                self.file_contents_string = infile.read()
        #  'inputFile.edn'
            data_with_wrapping_string_removed = json.load(self.file_contents_string)
            self.data = edn_format.loads(data_with_wrapping_string_removed)
        else:
            self.data = edn_format.loads(self.file_contents_string)
        '''
        #>>> edn_format.dumps({1, 2, 3})
        #'#{1 2 3}'
        
        return


class OutfileBase:
    def __init__(self):
        return
    
class OutfileHuman(OutfileBase): 
    def __init__(self, filePath):
        super().__init__()
        self.filePath = filePath
        return
    
    def show(self, data):
        print(transpilers.HumanTextTranspiler.convert_to_string(data))
        
    def get_text(self, data):
        return transpilers.HumanTextTranspiler.convert_to_string(data)
    
class OutfileQuantConnect(OutfileBase):
    def __init__(self):
        super().__init__()
        return

    def show(self, data):
        print(transpilers.QuantConnectTranspiler.convert_to_string(data))
        
    
#TODO finish    
class OutfileVectorBt(OutfileBase):
    def __init__(self):
        super().__init__()
        return

    def show(self, data):
        print(transpilers.VectorBTTranspiler.convert_to_string(data))
        

#TODO arg parser for inputs: input file, output file, output mode
def main()-> int:
    parser = argparse.ArgumentParser(description='Composer Symphony text parser')
    parser.add_argument('-i','--infile', dest="infile", action="store", help=' input file we read the symphony text from.  full path please', required=True)
    parser.add_argument('-o','--outfile', dest="outfile", action="store", default="OUTFILE", help=' output file to save the parsed text to.  if not given, will use stdout', required=False)
    parser.add_argument('-m','--mode', dest="mode", action="store", default="human", help=' output parsing mode to use.  if none given, will parse for "human readable output".  modes are: quantconnect, vectorbt, tradingview, thinkscript', required=False)
    parser.add_argument('-b', '--bulk', action="store_true", dest='bulk', default='False', help="it means the specified input is a filepath, containing a bulk list of urls, or filenames to process.  one url or file path per line")
    parser.add_argument('-u', '--url', action="store_true", dest='url', default='False', help="specifies that the input file path is actually the url to a shared, public symphony on composer.trade")
    parser.add_argument('-p', '--parent', action="store_true", dest='parent', default='False', help="specifies that we should try and look up the parents of this symphony, and get all previous copied information too.  only works if the 'infile' given was a url")
    
    
    args = vars(parser.parse_args())

    if args['url'] == True:
        url_list = []
        if args['bulk'] == True:
            # read bulk file and add them all to the "list"
            with open(args['infile'], 'r') as bulkfile:
                for line in bulkfile.readlines():
                    url_list.append(line)
        else:
            url_list.append(args['infile'])
            # just add the single one to the list and have it process the "list" anyways
        
        
        #todo move to request this from the composer site instead of hardcoding
        composerConfig = {
                "projectId" : "leverheads-278521",
                "databaseName" : "(default)"
            }
        total = len(url_list)
        for count, current_url in enumerate(url_list):
            
            print("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
            print("****************************************************************************************************************")
            print("                   starting a new bulk lookup                   %s of %s        " % (str(count), str(total)))
            print("****************************************************************************************************************")
            print("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
            
            m = re.search('\/symphony\/([^\/]+)', current_url)
            symphId = m.groups(1)[0]

            current_symph_id = symphId
            response_list = []
            while current_symph_id:
                symphReq = requests.get(f'https://firestore.googleapis.com/v1/projects/{composerConfig["projectId"]}/databases/{composerConfig["databaseName"]}/documents/symphony/{symphId}')
                resp = json.loads(symphReq.text)
                # 'latest_backtest_info', 'latest_backtest_edn', 'latest_version', 'hashtag', 'owner', 'description', 'created_at', 'latest_version_edn', 'sparkgraph_url', 'color', 'name', 'share-with-everyone?', 'stats', 'last_updated_at', 'youtube-url', 'cached_rebalance', 'latest_backtest_run_at', 'cached_rebalance_corridor_width', 'copied-from', 'backtest_url'])

                if 'fields' not in resp:
                    print("\r\nWas this a private symphony link? response 'object' had no 'fields' key.  could not parse\r\n  Error 2")
                    #sys.exit(2)
                    current_symph_id = None

                if args['parent'] == True:
                    if 'copied-from' in resp['fields']:
                        print("old id \r\n %s \r\nnew id \r\n %s\r\n" % (current_symph_id, resp['fields']['copied-from']['stringValue']))
                        if current_symph_id == resp['fields']['copied-from']['stringValue']:
                            print("copied from fields are the same, no more parents, ending the lookups")
                            # set current id to None, which should end our loop, and let us start looping over all our responses
                            current_symph_id = None
                        else:
                            # different parent id found, copy it, and then lets loop over and grab the next one
                            current_symph_id = resp['fields']['copied-from']['stringValue']
                    else:
                        current_symph_id = None
                    sleep_time = 2 + 20 * random.random()
                    print("-->random delay of %s between requests" % str(sleep_time))
                    time.sleep(sleep_time)

                # user did not ask for a "symphony parent lookup, so we will not try to loop over things
                else:
                    print("---> skipping symphony parent check")
                    current_symph_id = None
                # whatever the response was, copy it into our master response list.  we'll use all the responses later
                response_list.append(copy.deepcopy(resp))
            #import pdb; pdb.set_trace()

            for resp in response_list:
                print(json.dumps(resp['fields']['latest_version_edn']['stringValue'], indent=2))
                inFileParser = InFileReader(None, resp)
                inFileParser.printHeader(url_loaded = True)
                inFileParser.readFile(url_loaded = True)

                if args["mode"] == "human":
                    humanParser = OutfileHuman(args["infile"])
                    humanParser.show(inFileParser.root_node)

                if args["mode"] == "vector":
                    vectorParser = OutfileVectorBt()
                    vectorParser.show(inFileParser.data)

                if args["mode"] == "quantconnect":
                    quantconnectParser = OutfileQuantConnect()
                    humanParser = OutfileHuman(args["infile"])
                    quantconnectParser.show(
                        humanParser.get_text(inFileParser.root_node)
                    )

    else:
        file_list = []
        if args['bulk'] == True:
            # read bulk file and add them all to the "list"
            with open(args['infile'], 'r') as bulkfile:
                for line in bulkfile.readlines():
                    file_list.append(line)
        else:
            file_list.append(args['infile'])
            # just add the single one to the list and have it process the "list" anyways
            
            
        for file in file_list:
            print(file)
            inFileParser = InFileReader(file, None)
            inFileParser.readFile()


            if args["mode"] == "human":
                humanParser = OutfileHuman(file)
                humanParser.show(inFileParser.root_node)

            if args["mode"] == "vector":
                vectorParser = OutfileVectorBt()
                vectorParser.show(inFileParser.data)

            if args["mode"] == "quantconnect":
                quantconnectParser = OutfileQuantConnect()
                humanParser = OutfileHuman(args["infile"])
                quantconnectParser.show(
                    humanParser.show(inFileParser.root_node)
                )
    
    return 0
#TODO make generic class for output mode



#TODO make child classes for specific output modes


#TODO start listing out initial requirements for each specific output mode


if __name__ == '__main__':
    sys.exit(main()) 