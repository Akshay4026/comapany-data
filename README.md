
**Company data extraction , enricching ,Scoring**
__Technologies Used__
Prgramming lang - Python(FastAPi )
Automation      -  N8N workflow 
APIs            -  Govt registry data set API , Amazon S3 , Perplexity 
Storage         -  Amazon S3 bucket 
LLM             -  Perplexity pro
Docker 
**-----------------------------------------------------------------------------------------------------------------------------------**


__Work flow__
In n8n- 
start Node __Submission form__ triggers the flow on submission .Here I took just state from the user cause Registry data set API have only state as a parameter. So later we can add city in preprocessing.

2nd Node - __HTTP NODE__ developed a simple fastapi route(/company) which takes this state as a path parameter and fetcches it from registry.To avoid frequent api calls to registry .Better to download that whole data set as save it in S3 and return this s3 path .Reduces massive run time and computing while handling that huge __1,70,000__ records.
Here I only used 100 to fetch for testing cause while testing frequently may exhaust the credits which is unknown.

3rd Node - __HTTP NODE__ - this node route(/preprocessing) takes the S3 path from previous node reads it and extract only required company type.Honestly this registry data set is very messy.It is very difficult to find the IT related companies from  it even after adding many filters i can see few unrealted companies coming here.We can solve this by addding another perplexity call and removing unwanted service providing companies.this preproceses and return s3 path.

4th Node - __HTTP NODE__ - this node route(/enriching) takes the s3 path from previous node and reads data from that and ecnriches it -
focused mainly on fetching -
i)Size of compney
ii)L & D activities 
iii)Related services or not 
I used perplexity AI pro API for extracting this data I will explainn why i chose this after workflow.
it takes this info from perplexity ai enriches it and creates a new files uploads it into s3 and return the path. 

5th Node - __HTTP NODE__ - thiis node route(/rate) rates the echrinched data set based on 3 features i considered we can add few later 
i) L &D activity - 40% weightage
ii) size of company -35% weightage
iii)services matching - 25% weightage
saves this file in S3 and return path 

6th Node - __Final Node__: Final node where it simply take s3 path and downloads the json.
output - looks like :
<img width="379" height="242" alt="image" src="https://github.com/user-attachments/assets/68b4a0f5-9abb-49e6-b75c-29830199e5ca" />


I left the data to be in JSON cuase it is best form to add any other modifications or processing on them . So this is the only thing i did diff from task decription. Json formate is best to future works.
***Refer below image**
<img width="1315" height="663" alt="image" src="https://github.com/user-attachments/assets/ccf7a3f7-7433-4422-a092-142af101470e" />

**--------------------------------------------------------------------------------------------------------------------**

__Reasons__

Reason why I chose Perplexity AI : Perplexity AI is siply just a wrapper around the web pages along with LLM integration as i remember it uses claud ai antropy llm . 
so it can easily extract the webpages , blogs ,posts , news, own company websites very easily. 
<img width="970" height="731" alt="image" src="https://github.com/user-attachments/assets/9a3423c9-58ca-4fed-ac8f-19de116883a0" />
this is exactly how it extracts all the webpagges related to query.
It suits for better enrichment but not best for sure honestly . for more inclusive data we need to reply on paid API services like apollo. we can add them later .


I used microservices based architechure which is very much handly while scaling or adding more routes or features  or enriching api etc...

I will be honest the number in the list of 1,70,000 around records only 2k were useful to us .it is really very very hard to process these many records through api calls.If you agree we can download each of that dataset instead of api cll everytime.

Reason i chose this legit companies and CIN number which helps to spot company without any mistake .Goolge place api have many contraints so i iignored that


Please let me know if you need any clarification. we can setup a call to explain it indetail.




