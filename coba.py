from flask import Flask, request, make_response, Response
from waitress import serve
from stemming.porter2 import stem
import pandas as pd
from sklearn.feature_extraction.text  import CountVectorizer
from sklearn.cluster import KMeans
from io import BytesIO
import time
import zipfile
import numpy as np
import uuid
import os
import re

app = Flask(__name__)

def cleanse_text(text):
    if text:
        #remove unnesessary whitespace
        #example 'this product is    really good' become 'this product is really good'
        clean = ' '.join([i for i in text.split()])
        #stemming
        #misal caring jadi care, cats jadi cat
        red_text = [stem(word) for word in clean.split()]
        return ' '.join(red_text)
    else:
        return text

@app.route('/cluster',methods=['POST'])
def cluster():
    data = pd.read_csv(request.files['dataset'])
    unstructure = 'text'
    if 'col' in request.args:
        unstructure = request.args.get('col')
    no_of_clusters = 2
    if 'no_of_clusters' in request.args:
            no_of_clusters = request.args.get('no_of_clusters')
    data = data.fillna('NULL')
    data['clean_sum'] = data[unstructure].apply(cleanse_text)
    vectorizer = CountVectorizer(analyzer = 'word', stop_words="english")
    #calculate count word in each row
    counts = vectorizer.fit_transform(data['clean_sum'])
    k_means = KMeans(n_clusters = no_of_clusters)
    data['cluster_num'] = k_means.fit_predict(counts)
    data = data.drop(['clean_sum'],axis = 1)

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    data.to_excel(writer, sheet_name = 'Clusters', encoding = 'utf-8', index = False)

    clusters = []
    for i in range(np.shape(k_means.cluster_centers_)[0]):
        data_cluster = pd.concat([pd.Series(vectorizer.get_feature_names_out()),pd.DataFrame(k_means.cluster_centers_[i])], axis=1)
        data_cluster.columns = ['keywords','weights']
        data_cluster = data_cluster.sort_values(by = ['weights'],ascending = False)
        data_clust = data_cluster.head(n=10)['keywords'].tolist()
        clusters.append(data_clust)
    pd.DataFrame(clusters).to_excel(writer, sheet_name = "Top_Keywords",encoding = 'utf-8')

    data_pivot = data.groupby(['cluster_num'],as_index=False).size()
    data_pivot.name = 'size'
    data_pivot = data_pivot.reset_index()
    data_pivot.to_excel(writer, sheet_name = 'Cluster_Report', encoding = 'utf-8', index = False)

    workbook = writer.book
    worksheet = writer.sheets['Cluster_Report']
    chart = workbook.add_chart({'type': 'column'})
    chart.add_series({'values':'=Cluster_Report!$C$2:$C' + str(no_of_clusters+1)})
    worksheet.insert_chart('D2', chart)

    writer.save()

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file,'w') as zf:
        names = ['cluster_output.xlsx']
        files = [output]
        for i in range(len(files)):
            data = zipfile.ZipInfo(names[i])
            data.date_time = time.localtime(time.time())
            data.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(data, files[i].getvalue())
    memory_file.seek(0)
    response = Response(memory_file.getvalue(), mimetype = 'application/zip')
    response.headers['Content-Disposition'] = 'attachment;filename = cluster_output.zip'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


if __name__ == "__main__":
    serve(app, listen = '*:80')