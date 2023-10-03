
import sqlite3
import os
import logging
from utils.timer import Timer
import wandb

DB_BASE_PATH = os.path.abspath(
   os.path.join(os.path.dirname( __file__ ), '..', 'data/db/')
)

class DataLoader:
   current_db = ""
   conn = None
   cursor = None
   total_predicted_execution_time = 0
   total_gold_execution_time = 0

   def __init__(self):
      pass

   def execute_queries_and_match_data(self, sql, gold_sql, db_id):
      db_path = self.get_db_path(db_id)

      if self.current_db != db_id:
         self.conn = sqlite3.connect(db_path)
         self.cursor = self.conn.cursor()
         self.current_db = db_id
      
      try:
         with Timer() as t:
            self.cursor.execute(sql)
            pred_res = self.cursor.fetchall()
         
         if t.elapsed_time > 5:
            logging.info(f"Predicted query execution time: {t.elapsed_time:.2f} \nSQL Query:\n" + sql)
         else:
            logging.info(f"Predicted query execution time: {t.elapsed_time:.2f}")

         self.total_predicted_execution_time += t.elapsed_time

         wandb.log({"predicted_sql_execution_time": t.elapsed_time})

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
      
      self.total_gold_execution_time += t.elapsed_time

      wandb.log({"gold_sql_execution_time": t.elapsed_time})

      equal = (set(pred_res) == set(golden_res))
      if equal:
         return 1
      else:
         return 0
   

   def execute_query(self, sql, db_id):
      db_path = self.get_db_path(db_id)

      if self.current_db != db_id:
         self.conn = sqlite3.connect(db_path)
         self.cursor = self.conn.cursor()
         self.current_db = db_id
      
      try:
         with Timer() as t:
            self.cursor.execute(sql)
            pred_res = self.cursor.fetchall()
         wandb.log({"gold_sql_execution_time": t.elapsed_time})
         
         if t.elapsed_time > 5:
            logging.info(f"Query execution time: {t.elapsed_time:.2f} \nSQL Query:\n" + pred_res)
         else:
            logging.info(f"Query query execution time: {t.elapsed_time:.2f}")

      except sqlite3.Error as err:
         logging.error("DataLoader.execute_query() " + str(err))
         return 0

      return 1


   def list_tables_and_columns(self, db_name):
      if self.current_db != db_name:
         self.conn = sqlite3.connect(self.get_db_path(db_name))
         self.cursor = self.conn.cursor()

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


   def get_create_statements(self, db_name):   
      if self.current_db != db_name:
         self.conn = sqlite3.connect(self.get_db_path(db_name))
         self.cursor = self.conn.cursor()

      self.cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
      create_statements = self.cursor.fetchall()

      return '\n'.join([statement[0] for statement in create_statements])

   def get_db_path(self, db_name):
      return DB_BASE_PATH + '/' + db_name + '/' + db_name + '.sqlite'

    