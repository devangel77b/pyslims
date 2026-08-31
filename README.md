# Python code to import ISBNs into SLiMS 
### Dennis Evangelista, 2026

I would like to set up a library management system for my school's nerd 
program. During the pandemic they seem to have got rid of the library; 
it is now used for study hall and lunch, although they have started an
effort to provide books and have one corner with shelves. The Science
and Engineering program often needs very specialized, high level texts
which we actually have because alumni are nice and provide their old 
college engineering and advanced science books. As we bring the STEM lab
online, I am trying to reserve a corner there for the S&E Library, and
it will need some sort of LMS that is free, will run on the cloud alongside
our peer reviewed journal, and is able to run with minimal resources on a
a standard LAMPS stack. 

The options of of 2026 were Koha/Evergreen (too resource heavy); PMB (too 
French); OpenBiblio (required downgrade of php to 8.2 and still didn't work
right); and SLiMS. Based on tests on a local linux machine, SLiMS will
probably run, but its copy catalog tools do not seem to work. Library of 
Congress SRU imports are completely broken, MARC parsing seems off, and I 
have a hard time even getting it to import from hand-written csv as it
ignores the headers. There are too many bugs in their php code to patch. 

The last ditch solution is to write some Python code to inject records into
the mariadb mysql database directly. This code will take ISBNs, look them
up on a public server like Open Library, parse the returned records, and 
add them to the database without having to deal with any of the SLiMS code. 

## General approach
  1. Get ISBN numbers input from a text file or stdin. These can either be
  manually input or scanned using a barcode scanner.
  2. Use requests to get full bibliographic information. This part works. 
  3. (TODO) Inject the data into the database using pysql or similar. 
  
Hopefully, once the data is in the SLiMS database, SLiMS will be able to 
handle it from there. 

If this fails, the fallback/alternative positions are:
  1. TinyCat (already trying this)
  2. Make the students write their own. 

## Contributors

Dennis Evangelista
