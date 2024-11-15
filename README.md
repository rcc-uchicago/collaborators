# collaborators

This project provides an executable Python script `get_collaborators.py` that generates a list of coauthors of a given author name within a period. This could be helpful for preparing the Collaborators and Other Affiliations (COA) form for NSF grant submission.

The output contains the affiliation of each coauthor from Google Scholar (if any) and their ORCID (if any). If there are more than one ORCIDs for a coauthor name, it will give the URL with the query with the first and last names of the coauthor.

Contact: ndtrung at uchicago dot edu

### Installation
```
git clone https://github.com/rcc-uchicago/collaborators.git
cd collaborators
python3 -m venv my_venv
source ./my_venv/bin/activate
python3 -m pip install requests scholarly
```

### Usage
```   
python get_collaborators.py  -a "John A. Smith" -p 2022-2024 -t "John A Smith; Smith JA" -v
```
where
```
   -a: the name of the person, in this case, John A. Smith
   -p: the period to find the collaborators of the person, e.g., 2022-2024
   -t: a list of the possible variations of the person name that can be present in the publications
   -v: show verbose output
```

Output:
  - screen output
  - output file: `output.csv`


For more arguments, run
```
python get_collaborators.py  -h
```
