from flask import render_template
from bokeh.plotting import figure, show
from bokeh.embed import components, file_html
from bokeh.io import output_notebook
from bokeh.models import ColumnDataSource
from bokeh.transform import factor_cmap, factor_mark
from bokeh.resources import CDN
import numpy as np
import pandas as pd
import geopandas as gpd
import requests
from app import app

api_key='cr_pk_live_o4ovygBjeU4oCEu9rIqfIc777UA1Iz6k'
base_url='https://api.civicreview.com/public'
all_permits_url='https://api.civicreview.com/public/v1/permits'
params={'Authorization':'Bearer {}'.format(api_key)}
permit_url='https://api.civicreview.com/public/v1/permits?permitTypes[]={}'
building_permit_id='69850079f7872620069534e1'
permit_params={'Authorization':'Bearer {}'.format(api_key),'isActive':'true','permitTypes':building_permit_id}

@app.route('/')
@app.route('/index')
def index():
	response=requests.get(permit_url.format('{}&isActive=true'.format(building_permit_id)),headers=permit_params).json()
	df=pd.DataFrame(response)
	for index, row in df.iterrows():
		df.loc[index,'Project Type']=row['formData']['fields'][0]['value']
		df.loc[index,'Conditioned Square Footage']=row['formData']['fields'][2]['value']
		df.loc[index,'Garage Square Footage']=row['formData']['fields'][3]['value']
		df.loc[index,'Other Square Footage']=row['formData']['fields'][4]['value']
	df['Conditioned Square Footage']=df['Conditioned Square Footage'].astype(float)
	df['Garage Square Footage']=df['Garage Square Footage'].astype(float)
	df['Other Square Footage']=df['Other Square Footage'].astype(float)
	df['_created']=pd.to_datetime(df['_created'])
	fig=figure(title='Conditioned Square Footage', x_axis_type='datetime')
	fig.scatter(x="_created",
				y="Conditioned Square Footage",
				source=df,
				size=10,
				color=factor_cmap('Project Type','Category20_{}'.format(len(list(df['Project Type']))),list(df['Project Type'])),
				legend_group="Project Type")
	fig.add_layout(fig.legend[0], "above")
	fig.legend.ncols=len(df['Project Type'].unique())
	fig.legend.title="Project Type"
	return render_template('index.html',title='Home',fig=file_html(fig,CDN,"Plot"))