import pandas as pd
import numpy as np
import re
import pdfminer
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

def voter_registry(ocrfilename, df_name):
    #ocrfilename = name of file, either in the same folder or as a path
    #df_name = name of output

    unwanted_words = ["The City Record", "THE CITY RECORD", "OFFICIAL JOURNAL", "SUPPLEMENT", "LIST OF REGISTERED VOTERES", "BOROUGH OF"]
    col_names = ["Year", "AD", "ED", "Street", "Number", "Name"]
    voters = pd.DataFrame(columns=col_names)

    #xlsx file
    rawdata = pd.read_excel(ocrfilename, header=None)

    #replaces unwanted words as blank
    for idx, line in rawdata.iloc[:, 0].items():
        for word in unwanted_words:
            if fuzz.partial_ratio(line.strip(), word) >= 70:
                rawdata.set_value(idx, 0, "     ")
            else:
                pass
    #removes all space
    for idx, line in rawdata.iloc[:, 0].items():
        if line.isspace():
            rawdata.drop(rawdata.index[idx], inplace=True)

    rawdata.reset_index(drop=True, inplace=True)

    for idx, line in rawdata.iloc[:, 0].items():
        #combine hyphenated lines
        if ((line.strip()[-1:] == "-" or line.strip()[-1:] == "--")) and rawdata.iloc[idx+1, 0][0].islower():
            newline = rawdata.iloc[idx, 0] + rawdata.iloc[idx+1, 0]
            rawdata.set_value(idx, 0, newline)
            rawdata.set_value(idx+1, 0, "    ")
    #remove hyphens from names
    for idx, line in rawdata.iloc[:, 0].items():
        if "-" in line:
            rawdata.set_value(idx, 0, re.sub("-", "", line))

    rawdata.reset_index(drop=True, inplace=True)

    #removes all space
    tod = []
    for idx, line in rawdata.iloc[:, 0].items():
        if line.isspace():
            tod.append(idx)
    rawdata.drop(rawdata.index[tod], inplace=True)
    rawdata.reset_index(drop=True, inplace=True)

    #initialize values
    ad = "n/a"
    ed = "n/a"
    streetname = "n/a"
    year = 1902
    number = 0
    name = "n/a"
    lastname = "n/a"
    firstname = "n/a"
    idx = 0
    minitial = ""


    for line in rawdata.iloc[:, 0]:
        if line.isspace()==False:
            #all caps---either an ad, ed, maybe street/name
            capscheck = "".join(x for x in line if x.isupper())
            if len(capscheck) >=4: 
                if fuzz.partial_ratio(line, "ASSEMBLY") >= 70:
                    ad = line
                elif fuzz.partial_ratio(line, "ELECTION DIST.") >= 75 or fuzz.partial_ratio(line, "ELEC. DIST.") >= 70 or fuzz.partial_ratio(line, "ELECTION DISTRICT") >= 75:
                    ed = line
                else: 
                    #maybe a street or name 
                    lowercheck = "".join(x for x in line if x.islower())
                    if len(lowercheck) <= 3: 
                        streetname = line
                    else:
                        entry = line
                        number = "".join(x for x in entry if x.isdigit())
                        name = ''.join(i for i in entry if not i.isdigit())
            else:
                #for sure a name
                entry = line
                number = "".join(x for x in entry if x.isdigit())
                name = ''.join(i for i in entry if not i.isdigit())
            #new row to dataframe
            new_row = [year, ad, ed, streetname, number, name]
            voters.loc[len(voters), :] = new_row
        else:
            pass

    #fill in empty number rows
    for idx, num in voters.iloc[:, 4].items():
        if num == "":
            point = idx
            while point >= 0:
                #finds the nearest filled cell that is before it
                point -= 1
                val = voters.iloc[point, 4]
                if val is not "" and voters.iloc[idx, 3] == voters.iloc[point, 3]:
                    voters.set_value(idx, "Number", val)
                    break
    #another one to fill in missing numbers (but going forwards)
    for idx, num in voters.iloc[:, 4].items():
        if num == "":
            try:
                pt = idx
                while pt >= 0:
                    #finds the nearest filled cell that is after it
                    pt += 1
                    val = voters.iloc[pt, 4]
                    if val is not "" and voters.iloc[idx, 3] == voters.iloc[pt, 3]:
                        voters.set_value(idx, "Number", val)
                        break
            except:
                pass
    #clean up any misread numbers
    # for idx, number in voters.iloc[:, 4].items():
    #         #number smaller than the one before it and same street
    #         if float(number) < float(voters.iloc[idx-1, 4]) and (voters.iloc[idx-1, 3]) == (voters.iloc[idx, 3]):
    #             #similarity between surrounding numbers
    #             if fuzz.ratio(str(number), str(voters.iloc[idx-1, 4])) > fuzz.ratio(str(number), str(voters.iloc[idx+1, 4])):
    #                 voters.set_value(idx, "Number", voters.iloc[idx-1, 4])
    #             elif fuzz.ratio(str(number), str(voters.iloc[idx-1, 4])) < fuzz.ratio(str(number), str(voters.iloc[idx+1, 4])):
    #                 voters.set_value(idx, "Number", voters.iloc[idx+1, 4])
    #clean streets
    for idx, street in voters.iloc[:, 3].items():
        if "." in street:
            #get rid of the periods
            removep = re.sub("[.]", "", street)
            #remove special characters
            removesc = re.sub('[^a-zA-Z.,\d\s]', '', removep)
            #remove leading space
            newstreet = removesc.strip()
            voters.set_value(idx, "Street", newstreet)

    #clean names
    for idx, name in voters.iloc[:, 5].items():
        if "." in name:
            #get rid of the periods
            removep = re.sub("[.]", "", name)
            #remove special characters
            removesc = re.sub('[^a-zA-Z.,\d\s]', '', removep)
            #remove leading space
            newname = removesc.strip()
            voters.set_value(idx, "Name", newname)
    #remove end commas
    for idx, name in voters.iloc[:, 5].items():
        if name[-1:] == ",":
            removec = name[:-1].strip()
            #remove leading space
            voters.set_value(idx, "Name", removec)

    #lines with lone letters
    delete = []
    for idx, entry in voters.iloc[:, 5].items():
        if len(entry)==1:
            #most likely an initial
            voters.set_value(idx-1, "Name", voters.iloc[idx-1, 5] + entry)
            delete.append(idx)
    voters.drop(voters.index[delete], inplace=True)
    voters.reset_index(drop=True, inplace=True)

    #lone suffixes
    drop = []
    for idx, entry in voters.iloc[:, 5].items():
        if entry.strip() == "Rev" or entry == "Gen":
            #most likely an initial
            voters.set_value(idx-1, "Name", voters.iloc[idx-1, 5] + entry)
            drop.append(idx)
    voters.drop(voters.index[drop], inplace=True)
    voters.reset_index(drop=True, inplace=True)

    #isolate suffixes
    suffix = []
    for idx, name in voters.iloc[:, 5].items():
        if name[-2:].strip() == "Jr" or name[-2:].strip() == "Sr" or name[-2:].strip() == "jr" or  name[-2:].strip() == "sr":
            suffix.append(name[-2:].strip())
            voters.set_value(idx, "Name", name[:-2])
        elif name[-3:].strip() == "Rev" or name[-3:].strip== "rev":
            suffix.append(name[-3:].strip())
            voters.set_value(idx, "Name", name[:-3])
        else:
            suffix.append("")
    voters["Suffix"] = suffix

    #middle initial
    minitial = []
    for idx, name in voters.iloc[:, 5].items():
        mi = name[-1:]
        if mi.isupper() and len(re.findall(r'\w+', name)) == 3:
            minitial.append(mi)
            cleanname = name[:-1]
            voters.set_value(idx, "Name", cleanname)
        else:
            minitial.append("")
            voters.set_value(idx, "Name", name)
    voters["Middle"] = minitial
    #scrub commas at end
    for idx, name in voters.iloc[:, 5].items():
        if name.strip()[-1:] == ",":
            voters.set_value(idx, "Name", name.strip()[:-1])

    #reindex
    voters.reset_index(drop=True, inplace=True)

    #scrub letters before first capital letter
    for idx, name in voters.iloc[:, 5].items():
            voters.set_value(idx, "Name", re.sub("^.*?([A-Z])", "\\1", name))

    #last name first name
    lname = []
    fname = []
    for idx, name in voters.iloc[:, 5].items():
        #comma (x, y)
        if bool(re.match(r"(?x) ^ [\w ']+ , [\w ']+ $ ", name)):
            #everything before comma = last, everything after= first
            lname.append(name.split(',')[0].strip())
            fname.append(name.split(',')[1].strip())
        #comma at end (x, y y,)
        elif bool(re.match(r"(?x) ^ [\w ']+ , [\w ']+ ,$ ", name)):
            lname.append(name.split(',')[0].strip())
            fname.append(name.split(',')[1].strip())
        #period (x.y)
        elif bool(re.match(r"(?x) ^ [\w ']+ \. [\w ']+ $ ", name)):
            lname.append(name.split('.')[0].strip())
            fname.append(name.split('.')[1].strip())
        #space (x y)
        elif bool(re.match(r"([A-Za-z']+)+ ([A-Z][A-Za-z']+)", name)):
            grouped = re.match(r"([A-Za-z']+)+ ([A-Z][A-Za-z']+)", name).groups()
            lname.append(grouped[0].strip())
            fname.append(grouped[1].strip())
        #nospace (SmithJohn)
        elif bool(re.match(r"([A-Za-z']+)([A-Z][A-Za-z']+)", name)):
            full = re.match(r"([A-Za-z']+)([A-Z][A-Za-z']+)", name).groups()
            lname.append(full[0])
            fname.append(full[1])
        else:
            lname.append("")
            fname.append("")
    #add lname fname to voters
    voters["Last"] = lname
    voters["First"] = fname

    #try to fix names again:
    for idx, name in voters.iloc[:, 5].items():
        if voters.iloc[idx, 6] == "" and voters.iloc[idx, 7] == "":
            new = name.split(",")
            newp = name.split(".")
            if len(new) == 2:
                voters.set_value(idx, "Last", new[0].strip())
                voters.set_value(idx, "First", new[1].strip())
            if len(newp) == 2:
                voters.set_value(idx, "Last", newp[0].strip())
                voters.set_value(idx, "First", newp[1].strip())
    # lone letters and suffixes

    #drop rows with n/a name
    for idx, name in voters.iloc[:, 5].items():
        if name == "n/a":
            voters = voters.drop([idx])
    voters.reset_index(drop=True, inplace=True)

    #scrub repeats and empty fname lname
    todelete = []
    for idx, name in voters.iloc[:, 5].items():
        try:
            if name == voters.iloc[idx-1, 5]:
                todelete.append(idx)
        except:
            pass
    voters.drop(voters.index[todelete], inplace=True)
    voters.reset_index(drop=True, inplace=True)
    td = []
    for idx, name in voters.loc[:, "Last"].items():
        if name == "" and voters.loc[idx, "First"] == "":
            td.append(idx)
    voters.drop(voters.index[td], inplace=True)

    voters.reset_index(drop=True, inplace=True)

    #fixing ED/AD
    ad = 1
    ed = 1
    clean_ad = []
    for idx, assembly in voters.iloc[:, 1].items():
        if idx == 0:
            clean_ad.append(ad)
        else:
            if assembly == voters.iloc[idx-1, 1]:
                clean_ad.append(ad)
            elif assembly != voters.iloc[idx-1, 1]:
                ad += 1
                clean_ad.append(ad)
    clean_ed = []
    for idx, election in voters.iloc[:, 2].items():
        if idx == 0:
            clean_ed.append(ed)
        else:
            if voters.iloc[idx, 1] != voters.iloc[idx-1, 1]:
                #reset ed counter
                ed = 1
            if election == voters.iloc[idx-1, 2]:
                clean_ed.append(ed)
            elif election != voters.iloc[idx-1, 2]:
                ed += 1
                clean_ed.append(ed)
    #add to df
    voters["ADedit"] = clean_ad
    voters["EDedit"] = clean_ed

    #rearrange columns 
    finalvoters = voters[['Year', 'AD', 'ED', 'ADedit', "EDedit", "Street", "Number", "Name", "Last", "First", "Middle", "Suffix"]]

    #output name
    finalvoters.to_excel(df_name)
    print('voter registry processed!')

voter_registry("1902manhattan.xlsx", "1902manhattanfinal.xlsx")
