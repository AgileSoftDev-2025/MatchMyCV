import mysql.connector

def getConnection():
    conn =mysql.connector.connect(
        database='db_jobs', 
        user='root', 
        password='', 
        host='localhost', 
        port='3306',
        # database='u116665791_db_jobs_scrape', 
        # user='u116665791_admin', 
        # password='aryaRiski123', 
        # host='31.220.110.101', 
        # port='3306',
    )
    return conn


def insertData(data_df, tableName):
    conn = getConnection()
    cursor = conn.cursor()
    try:     
        cur = conn.cursor()     
        for index, row in data_df.iterrows():         
            title = row["title"]        
            company = row["company"]         
            location = row["location"]         
            requirement = row["requirement"]      
            posted = row["posted"]
            image = row["image"] 
            link = row["link"]            
            date_posted = row['date_posted']
            try:             
                query = """INSERT into jobs_search_jobs(title,company,location,requirement,posted,date_posted,image,link) VALUES (%s,%s,%s,%s,%s,%s,%s,%s);"""            
                column = (title, company, location, requirement, posted, date_posted, image, link)             
                cursor.execute(query, column)         
            except mysql.connector.IntegrityError:             
                conn.rollback()
            else:                                
                conn.commit()
                
            cur.close() 
    except Exception:     
        print("error", Exception[0])
 
def removeDuplicate(tableName):
    conn = getConnection()
    cur= conn.cursor()
    query_duplicate = """DELETE D1 FROM jobs_search_jobs D1 INNER JOIN jobs_search_jobs D2 WHERE D1.job_id < D2.job_id AND D1.title = D2.title AND D1.company = D2.company AND D1.link = D2.link;"""
    
    cur.execute(query_duplicate)
    conn.commit()
    cur.close()
    conn.close()