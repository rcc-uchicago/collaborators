#!/usr/bin/env python
# Generate a list of coauthors of a given author name starting from a given year to present
#
# How to use:
#     cd /project/rcc/shared/coa-form
#     module load python/anaconda-2023.09
#     source /project/rcc/shared/common-env/bin/activate
#     python collaboators.py  -v -a "Erin J. Adams" -p 2022-2024 -t "Erin J Adams" -o output-ejadams.csv
#
# Contact: ndtrung@uchicago.edu

from argparse import ArgumentParser
from multiprocessing import Process, Pool
import requests
from scholarly import scholarly
import time
def search_orcid_by_full_name(first_name, last_name, middle_name=None):
    # Base URL for the ORCID public API
    base_url = "https://pub.orcid.org/v3.0/search"
    headers = {
        "Accept": "application/json"  # Set response format to JSON
    }
    
    # Build query with first name, last name, and optionally middle name
    query = f"given-names:{first_name} AND family-name:{last_name}"
    if middle_name:
        query += f" AND other-names:{middle_name}"

    params = {"q": query}
    response = requests.get(base_url, headers=headers, params=params)

    if response.status_code == 200:
        results = response.json()
        records = results.get("result", [])
        if not records:
            return None
        
        people = []
        # Fetch detailed information for each ORCID iD
        for record in records:
            orcid_id = record.get("orcid-identifier", {}).get("path")
            
            if orcid_id:
                detailed_info = fetch_detailed_profile(orcid_id)
                people.append(detailed_info)
                
        return people
    else:
        return f"Error: {response.status_code} - {response.text}"

def fetch_detailed_profile(orcid_id):
    # URL for fetching individual ORCID profile
    profile_url = f"https://pub.orcid.org/v3.0/{orcid_id}/person"
    headers = {"Accept": "application/json"}
    
    response = requests.get(profile_url, headers=headers)
    if response.status_code == 200:
        profile_data = response.json()
        
        # Extract name details
        given_name = profile_data.get("name", {}).get("given-names", {}).get("value", "N/A")
        family_name = profile_data.get("name", {}).get("family-name", {}).get("value", "N/A")

        # Extract affiliation details (institutions)
        affiliations = []
        affiliation_group = profile_data.get("affiliations", {}).get("affiliation-group", [])
        
        if affiliation_group:
            for affiliation in affiliation_group:
                org_name = affiliation.get("organization", {}).get("name", "N/A")
                affiliations.append(org_name)
        else:
            affiliations.append("No affiliations available")
        
        # Combine name and affiliations
        return {
            "ORCID iD": orcid_id,
            "Name": f"{given_name} {family_name}",
            "Affiliations": affiliations
        }
    else:
        return {"ORCID iD": orcid_id, "Name": "N/A", "Affiliations": "N/A"}


# get the affiliation of a collaborator/coauthor name
def get_affiliation(name):
    try:
        # Search for the author by name
        #coauthors_affiliations = []
        affiliations = []
        search_query = scholarly.search_author(name)
        # get the top 5 names that match
        for i in range(5):
            author = next(search_query, None)  
            if author:
                # Fill in the author details to retrieve complete info
                author = scholarly.fill(author)
                author_name = author.get('name', 'Name not found')
                # ensure that the name is matching
                if author_name.lower() == name.lower():
                    affiliation = author.get('affiliation', 'Affiliation not found')
                    #affiliations.append(affiliation)

                    full_name = name.split(' ')
                    n = len(full_name)
                    first_name = full_name[0]
                    last_name = full_name[n-1]
                    results = search_orcid_by_full_name(first_name, last_name)

                    orcids = []
                    if results:
                        num_results = len(results)
                        if num_results == 1:
                            info = "Found ORCID: "
                            for person in results:
                                url = f"https://orcid.org/{person['ORCID iD']}"
                                orcids.append(url)
                            info += "; ".join(orcids)                        
                        else:
                            info = "Found multiple ORCID(s): "
                            info += f"https://orcid.org/orcid-search/search?searchQuery={first_name}%20{last_name}"

                    affiliation += ", " + info
                    affiliations.append(affiliation)

        if not affiliations:
            full_name = name.split(' ')
            n = len(full_name)
            first_name = full_name[0]
            last_name = full_name[n-1]
            if len(full_name) > 2:
                middle_name = ""
                for i in range(1,n-1):
                    middle_name += full_name[i] + " "
            
            results = search_orcid_by_full_name(first_name, last_name)
            if not results:
                info = f"Affiliation not found on Google Scholar nor ORCID (https://orcid.org/orcid-search/search?searchQuery={first_name}%20{last_name})"
                return [info]

            info = "Affiliation not found on Google Scholar; "
            orcids = []
            if results:
                num_results = len(results)
                if num_results == 1:
                    info += "Found ORCID: "
                    for person in results:
                        url = f"https://orcid.org/{person['ORCID iD']}"
                        orcids.append(url)
                    info += "; ".join(orcids)                        
                else:
                    info += "Found multiple ORCID(s): "
                    info += f"https://orcid.org/orcid-search/search?searchQuery={first_name}%20{last_name}"
            
            return [info]

        return affiliations

    except Exception as e:
        return f"An error occurred: {e}"

# get the coauthors of a given name from the start_year
def get_coauthors(name, name_variations, start_year, end_year, verbose=True):
    try:
        
        coauthor_list = []
        # Search for the author by name
        search_query = scholarly.search_author(name)
        for i in range(5):
            author = next(search_query, None)
            if author:
                # Fill in the author details to retrieve complete info
                author = scholarly.fill(author)
                author_name = author.get('name', 'Name not found')
                if author_name.lower() == name.lower():
                    print(f"Found information for {author_name}")
                    print(f"Getting all the pulications from Google Scholar and ORCID ...")
                    # Retrieve and list all publications with co-authors
                    papers = []
                    counter = 0
                    publications = author.get('publications', [])
                    sorted_publications = sorted(
                        publications,
                        key=lambda pub: int(pub.get('bib', {}).get('pub_year', 0)),  # Default year to 0 if missing
                        reverse=True  # Sort by descending order
                    )

                    #print(f"Found {len(publications)} in total")
                    print(f"Scanning the publications for unique coauthors {start_year} to {end_year}")
                    for publication in sorted_publications:
                        publication = scholarly.fill(publication)
                        title = publication.get('bib', {}).get('title', 'Title not found')
                        year = publication.get('bib', {}).get('pub_year', 'Year not found')
                        venue = publication.get('bib', {}).get('venue', 'Venue not found')
                        coauthors = publication.get('bib', {}).get('author', 'Authors not found')
                        
                        if year == "Year not found":
                            continue

                        # break if the publication year is earlier than start_year
                        if int(year) < start_year:
                            break

                        # skip if the publication year is more recent than end_year (>= start_year)
                        if int(year) > end_year:
                            continue

                        papers.append({
                            "title": title,
                            "year": year,
                            "venue": venue,
                            "authors": coauthors
                        })
                        #print(coauthors)

                        coauthors = coauthors.split(' and ')
                        for aut in coauthors:
                            aut_name = aut.replace('.','')
                            aut_name = aut_name.strip()

                            if aut_name not in coauthor_list and aut_name.lower() != name.lower():
                                if aut_name not in name_variations:
                                    coauthor_list.append(aut_name)

                        counter = counter + 1
                        if verbose == True:
                            print(f"{counter}. {title}, {year}")

                    print(f"There are {counter} publications within {start_year}-{end_year}")

        return coauthor_list

    except Exception as e:
        return f"An error occurred: {e}"

# find affiliation of a names subset, return a list of tuples (the collaborator name, their affiliation)
def process_collaborators(names_subset):
    return [(name, get_affiliation(name)) for name in names_subset]

# run multiprocessing
def run_mutiprocesing(collaborator_list, num_workers):
    # Calculate chunk size and divide the list into chunks for each worker
    chunk_size = len(collaborator_list) // num_workers
    chunks = [collaborator_list[i * chunk_size: (i + 1) * chunk_size] for i in range(num_workers)]
    
    # Handle any remaining names in the list (if length isn't perfectly divisible)
    if len(collaborator_list) % num_workers != 0:
        chunks[-1].extend(collaborator_list[num_workers * chunk_size:])

    # Initialize a pool of workers
    #with Pool(num_workers) as pool:
    #    # Map the process_collaborators function to each chunk
    #    results = pool.map(process_collaborators, chunks)

    p1 = Process(target=process_collaborators, args=(1,))
    p2 = Process(target=process_collaborators, args=(2,))
    
    # Flatten the results list to combine all outputs from each worker
    combined_results = [affiliation for sublist in results for affiliation in sublist]

    return combined_results


if __name__ == "__main__":
    
    author_name = "Trung Dac Nguyen"
    verbose = True
    start_year = 2022
    end_year = 2024
    name_variations = []
    num_workers = 1
    outputfile = "output.csv"

    parser = ArgumentParser()
    parser.add_argument("-a", "--author-name", dest="author_name", default="", help="Author name")
    parser.add_argument("-t", "--variations",  dest="variations",  default="", help="Author name variations")
    parser.add_argument("-p", "--period",      dest="period",      default="", help="Period for publications, default 2022-2024")
    parser.add_argument("-n", "--num-workers", dest="num_workers", default=1, help="Number of workers, default 1")
    parser.add_argument("-o", "--output-file", dest="outputfile",  default=outputfile, help="Output file, csv format")
    parser.add_argument("-v", "--verbose",     dest="verbose",     default=False, action='store_true', help="Verbose output")
    
    args = parser.parse_args()
    author_name = args.author_name
    verbose = args.verbose
    num_workers = int(args.num_workers)
    outputfile = args.outputfile

    if args.variations != "":
        name_variations = args.variations.split(';')
    name_variations.append(author_name)

    if args.period:
        years = args.period.split("-")
        
        start_year = int(years[0])
        end_year = int(years[1])
    
    if author_name == "":
        print(f"Need an author name (-a \"John Doe\")")
        quit

    print(f"Search for {author_name} on Google Scholar ...")
    coauthor_list = get_coauthors(author_name, name_variations, start_year, end_year, verbose)

    num_coauthors = len(coauthor_list)
    print(f"Found {num_coauthors} colloborators")

    start = time.time()
    if num_workers > 1:
        print(f"Finding collaborator affiliations from Google Scholar with {num_workers} workers in parallel ...")
        results = run_mutiprocesing(coauthor_list, num_workers)
        print("List of collaborators:")
        counter = 1
        with open(outputfile, "w") as f:
            for name, affiliation in results:
                aff = ";".join(affiliation)
                print(f"{counter}. {name}, {aff}")
                f.write(f"{name}; {aff}\n")
                counter = counter + 1
    else:
        print(f"Finding collaborator affiliations from Google Scholar ...")
        print("List of collaborators:")
        counter = 1
        with open(outputfile, "w") as f:
            for name in coauthor_list:
                if name:
                    affiliations = get_affiliation(name)
                    if affiliations:
                        print(f"{counter}. {name}, {affiliations[0]}")
                        f.write(f"{name}; {affiliations[0]}\n")
                    counter = counter + 1
    end = time.time()
    print('Elapsed time for affiliation search (seconds): ', end - start)
