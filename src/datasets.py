
import sqlite3
import os
import logging
from utils.timer import Timer
from config import config
from utils.utils import load_json



class Dataset:
   """
   A class to load and manage text-to-SQL datasets.
   """

   BASE_DB_PATH = None
   DATA_PATH = None

   def __init__(self):
      self.current_db = ""
      self.conn = None
      self.cursor = None
      self.data = []
      self.total_predicted_execution_time = 0
      self.total_gold_execution_time = 0
      self.last_predicted_execution_time = 0
      self.last_gold_execution_time = 0

      self.current_database_schema = ""

      self.load_data()


   def load_data(self):
      """
      Load questions from the predefined DATA_PATH.

      Raises:
         DataLoaderError: If DATA_PATH is not defined.
      """
      if self.DATA_PATH is None:
         raise ValueError("DATA_PATH must be defined in child classes")

      data = load_json(self.DATA_PATH)      

      self.data = data

   
   def get_number_of_data_points(self):
      """
      Return the total number of questions available.
      
      Returns:
         int: The total number of questions.
      """
      return len(self.data)
   

   def get_data_point(self, index: int) -> dict:      
      """
      Retrieve a data point based on the provided index.

      Parameters:
         index (int): The index of the desired data point.

      Returns:
         dict: The retrieved data point.
      """
         
      return self.data[index]

   
   def execute_queries_and_match_data(self, sql: str, gold_sql: str, db_name: str) -> int:
      """
      Execute provided SQL queries and compare the results.

      Parameters:
         sql (str): The predicted SQL query to execute.
         gold_sql (str): The golden SQL query to compare results.
         db_name (str): The database name on which the queries will be executed.

      Returns:
         int: 1 if the results match, otherwise 0.
      """

      if self.current_db != db_name:
         self.load_db(db_name)
      
      try:
         with Timer() as t:
            self.cursor.execute(sql)
            pred_res = self.cursor.fetchall()
         
         if t.elapsed_time > 5:
            logging.info(f"Predicted query execution time: {t.elapsed_time:.2f} \nSQL Query:\n" + sql)
         else:
            logging.info(f"Predicted query execution time: {t.elapsed_time:.2f}")

         self.last_predicted_execution_time = t.elapsed_time
         self.total_predicted_execution_time += t.elapsed_time               

      except sqlite3.Error as err:
         logging.error("DataLoader.execute_queries_and_match_data() " + str(err))
         return 0

      with Timer() as t:
         self.cursor.execute(gold_sql)
         golden_res = self.cursor.fetchall()

      if t.elapsed_time > 5:
         logging.info(f"Golden query execution time: {t.elapsed_time:.2f} \nSQL Query:\n" + golden_res)
      else:
         logging.info(f"Golden query execution time: {t.elapsed_time:.2f}")
      
      self.last_gold_execution_time = t.elapsed_time
      self.total_gold_execution_time += t.elapsed_time      

      equal = (set(pred_res) == set(golden_res))
      return int(equal)
   

   def execute_query(self, sql: str, db_name: str) -> int:
      """
      Execute a SQL query on a specified database and log execution time.

      Parameters:
         sql (str): The SQL query to execute.
         db_name (str): The database name on which the query will be executed.

      Returns:
         int: 1 if the query executes successfully, otherwise 0.
      """
      
      if self.current_db != db_name:
         self.load_db(db_name)
      
      try:
         with Timer() as t:
            self.cursor.execute(sql)
            pred_res = self.cursor.fetchall()
         #wandb.log({"gold_sql_execution_time": t.elapsed_time})
         
         if t.elapsed_time > 5:
            logging.info(f"Query execution time: {t.elapsed_time:.2f} \nSQL Query:\n" + pred_res)
         else:
            logging.info(f"Query query execution time: {t.elapsed_time:.2f}")

      except sqlite3.Error as err:
         logging.error("DataLoader.execute_query() " + str(err))
         return 0

      return 1


   def list_tables_and_columns(self, db_name: str) -> str:
      """
      List tables and columns of a specified database, logging the info.

      Parameters:
         db_name (str): The database name to list tables and columns.

      Returns:
         str: The formatted string of tables and columns information.
      """
   
      if self.current_db != db_name:
         self.load_db(db_name)

      self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
      tables = self.cursor.fetchall()

      res = ""
      for table in tables:
         table_name = table[0]
         res = res + f"Table: {table_name}\n"
         
         self.cursor.execute(f"PRAGMA table_info(\"{table_name}\");")
         columns = self.cursor.fetchall()
         for column in columns:
               col_name = column[1]
               col_type = column[2]
               res = res + f"  Column: {col_name}, Type: {col_type}\n"         

      logging.info(res)
      return res              


   def get_create_statements(self, db_name: str) -> str:
      """
      Retrieve and store SQL CREATE statements for all tables in a database.

      Parameters:
         db_name (str): The name of the database to get CREATE statements.

      Returns:
         str: The SQL CREATE statements for all tables in the database.
      """
      if self.current_db != db_name:
         self.load_db(db_name)

         self.cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
         create_statements = self.cursor.fetchall()

         self.current_database_schema = '\n'.join([statement[0] for statement in create_statements])
      
      return self.current_database_schema
   

   def get_schema_and_sample_data(self, db_name: str) -> str:
      """
      Retrieve, store, and return the schema and sample data from a database.

      Parameters:
         db_name (str): The name of the database to get schema and data.

      Returns:
         str: A formatted string containing schema and sample data.
      """
       
      if self.current_db != db_name:
         self.load_db(db_name)      
      
         self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
         tables = self.cursor.fetchall()
         
         schema_and_sample_data = ""

         for table in tables:
            table = table[0]  
            self.cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}';")
            create_statement = self.cursor.fetchone()[0]
            
            schema_and_sample_data += f"{create_statement};\n\n"
            
            self.cursor.execute(f"SELECT * FROM \"{table}\" LIMIT 3;")
            rows = self.cursor.fetchall()
                     
            self.cursor.execute(f"PRAGMA table_info(\"{table}\");")
            columns = self.cursor.fetchall()
            column_names = [column[1] for column in columns]
            column_names_line = "\t".join(column_names)
            
            schema_and_sample_data += f"Three rows from {table} table:\n"
            schema_and_sample_data += f"{column_names_line}\n"

            for row in rows:
                  row_line = "\t".join([str(value) for value in row])
                  schema_and_sample_data += f"{row_line}\n"
            schema_and_sample_data += "\n"

         schema_and_sample_data += "\n"

         self.current_database_schema = schema_and_sample_data
    
      return self.current_database_schema


   def load_db(self, db_name: str) -> None:
      """
      Load a database into the class by connecting and setting a cursor.

      Parameters:
         db_name (str): The name of the database to load.
      """
      db_path = self.get_db_path(db_name)
      logging.debug("DB_path: " + db_path)
      self.conn = sqlite3.connect(db_path)      
      self.cursor = self.conn.cursor()
      self.current_db = db_name


   def get_db_path(self, db_name: str) -> str:
      """
      Construct and return the path to a specified database file.

      Parameters:
         db_name (str): The name of the database to find the path.

      Returns:
         str: The constructed path to the database file.

      Raises:
         ValueError: If BASE_PATH is not defined.
      """
   
      if self.BASE_DB_PATH is None:
         raise ValueError("BASE_PATH must be defined in child classes")
      return f"{self.BASE_DB_PATH}/{db_name}/{db_name}.sqlite"
   

   def get_data_path(self) -> str:
      """
      Abstract method to get the path for the data file.

      This method should be implemented in child classes.

      Raises:
         NotImplementedError: If the method is not implemented in a child class.
      """
      
      raise NotImplementedError("get_data_path() must be defined in child classes")
   

class BIRDDataset(Dataset):
   """
   Dataset class for the BIRD dataset.
   """

   BASE_DB_PATH = os.path.abspath(
      os.path.join(os.path.dirname( __file__ ), '..', 'data/BIRD/dev/dev_databases/'))

   TRAIN_DATA_PATH = os.path.abspath(
    os.path.join(os.path.dirname( __file__ ), '..', 'data/BIRD/dev/dev.json'))

   DEV_DATA_PATH = os.path.abspath(
    os.path.join(os.path.dirname( __file__ ), '..', 'data/BIRD/dev/dev.json'))
   
   def load_data(self) -> None:
      """
      Load and filter questions specific to the BIRD dataset configurations.
      """

      if self.TRAIN_DATA_PATH is None or self.DEV_DATA_PATH is None:
         raise ValueError("QUESTIONS_PATH must be defined in child classes")

      data = load_json(self.DEV_DATA_PATH)
      data = [data_point for data_point in data if data_point['db_id'] in config.bird_dev_domains]
      data = [data_point for data_point in data if data_point['difficulty'] in config.bird_difficulties]

      self.data = data


   def get_dev_domains(self):
      dev_data = load_json(self.DEV_DATA_PATH)
      
      domains = set()
      for data_point in dev_data:
         domains.add(data_point['db_id'])
      
      return "\n".join([domain for domain in sorted(domains)])


class SpiderDataset(Dataset):
   """
   Dataset class for the Spider dataset.
   """
   
   BASE_DB_PATH = os.path.abspath(
      os.path.join(os.path.dirname( __file__ ), '..', 'data/Spider/database/'))

   TRAIN_DATA_PATH = os.path.abspath(
      os.path.join(os.path.dirname( __file__ ), '..', 'data/Spider/train_spider.json'))
   
   DEV_DATA_PATH = os.path.abspath(
      os.path.join(os.path.dirname( __file__ ), '..', 'data/Spider/dev.json'))
   
   def load_data(self) -> None:
      """
      Load and filter questions specific to the Spider dataset configurations.
      """

      if self.TRAIN_DATA_PATH is None or self.DEV_DATA_PATH is None:
         raise ValueError("DATA_PATH must be defined in child classes")

      data = load_json(self.TRAIN_DATA_PATH)
      train_data = [data_point for data_point in data if data_point['db_id'] in config.spider_train_domains]
      dev_data = [data_point for data_point in data if data_point['db_id'] in config.spider_dev_domains]

      self.data = train_data + dev_data


   def get_data_point(self, index: int) -> None:
      """
      Retrieve a data point from the Spider dataset, adjusting SQL information.

      Parameters:
         index (int): The index of the desired question.

      Returns:
         dict: The selected question with modified SQL data.
      """

      data_point = self.data[index]
      data_point['SQL'] = data_point['query']
      data_point['evidence'] = ""
      del data_point['query']
      return data_point
   

   def get_train_domains(self):
      train_data = load_json(self.TRAIN_DATA_PATH)
      
      domains = set()
      for data_point in train_data:
         domains.add(data_point['db_id'])
      
      return "\n".join([domain for domain in sorted(domains)])


   def get_dev_domains(self):
      dev_data = load_json(self.DEV_DATA_PATH)
      
      domains = set()
      for data_point in dev_data:
         domains.add(data_point['db_id'])
      
      return "\n".join([domain for domain in sorted(domains)])
      


DATASET_LOADERS = {
    'BIRD': BIRDDataset,
    'Spider': SpiderDataset,
}

def get_dataset(dataset_name):
    return DATASET_LOADERS.get(dataset_name, Dataset)()