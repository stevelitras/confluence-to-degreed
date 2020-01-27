from utils import *
import logging
import json
import hashlib
import sys
import tempfile
import csv
from collections import OrderedDict
from requests.auth import HTTPBasicAuth

# Setting up some pseudo constants
LOG_LEVEL = logging.INFO if ("DEBUG" not in os.environ) else logging.DEBUG

#logging.basicConfig(format='%(asctime)s - %(message)s', level=LOG_LEVEL)
root = logging.getLogger()
root.setLevel(LOG_LEVEL)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(LOG_LEVEL)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

def lambda_handler(event, context):
  config = getParamInfo()
  template_values(config,config,tokens)
  
  pathway_sql = 'select "learningtools"."adsuserinfo".email as send_to, "confluencetodegreed".degreed_articles.url as wiki_url, "learningtools"."degreed_published_pathway_summary"."title" as "pathway_title" from "confluencetodegreed".degreed_articles left join wiki_spaces on "confluencetodegreed".degreed_articles.url=wiki_spaces.url left join "learningtools"."degreed_published_pathway_details" on "learningtools"."degreed_published_pathway_details"."content_id"="confluencetodegreed".degreed_articles.contentid left join "learningtools"."degreed_published_pathway_summary" on  "learningtools"."degreed_published_pathway_summary"."pathway_id"="learningtools"."degreed_published_pathway_details"."pathway_id" left join "learningtools"."adsuserinfo" on  "learningtools"."degreed_published_pathway_summary"."created_by"=concat("learningtools"."adsuserinfo"."first_name", ' ', "learningtools"."adsuserinfo"."last_name") where wiki_spaces.contentid is null and email is not null'
  to_upsert_sql = "select * from (select 'Article' as ContentType, \"confluencetodegreed\".wiki_spaces.contentid as ContentId, \"confluencetodegreed\".wiki_spaces.url as URL, 'N' as \"Delete\", \"confluencetodegreed\".wiki_spaces.title as Title from \"confluencetodegreed\".wiki_spaces union all select 'Article' as ContentType, \"confluencetodegreed\".degreed_articles.contentid as ContentId, \"confluencetodegreed\".degreed_articles.url as URL, 'Y' as \"Delete\", \"confluencetodegreed\".degreed_articles.title as Title from \"confluencetodegreed\".degreed_articles left join \"confluencetodegreed\".wiki_spaces on \"confluencetodegreed\".degreed_articles.url=\"confluencetodegreed\".wiki_spaces.url where \"confluencetodegreed\".wiki_spaces.contentid is null)"
  
  config['athena_db'] = "confluencetodegreed"

  results = athena_query(config, to_upsert_sql)
  logging.debug("Results: %s" % results)
  logging.info("Result Count: %d" % len(results))
  if (len(results) < 2):
    logging.info("No Data Found - No File being Generated")
  else:
    tblhdrs_meta = results.pop(0)['Data']
    rows = results


    logging.debug("Return from query: %s" % json.dumps(rows))
    if (len(rows) <= 1):
      logging.info("No Data Found - No File being Generated")
    else:
      fieldnames = []
      for hdr in tblhdrs_meta:
        fieldnames.append(hdr['VarCharValue'])

      filename = "Content_Update_File_%s.csv" % date.today().isoformat().replace('-','')

      with open("/tmp/%s" % filename, 'w') as fp:

        logging.info("Fieldnames: %s" % fieldnames)
        writer = csv.DictWriter(fp, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()

        for rowcont in rows:
          row_dict = OrderedDict()
          row = rowcont['Data']

          logging.info("Row: %s" % row)

          for itm in range(0, len(row)):
            if 'VarCharValue' in row[itm]:
              row_dict[fieldnames[itm]] = row[itm]['VarCharValue']
            else:
              row_dict[fieldnames[itm]] = ""
          logging.info("ROW DICT: %s", json.dumps(row_dict))
          writer.writerow(row_dict)