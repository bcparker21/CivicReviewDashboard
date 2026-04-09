from flask import render_template
from bokeh.plotting import figure, show
from bokeh.embed import components, file_html
from bokeh.io import output_notebook
from bokeh.models import ColumnDataSource, Tooltip, HoverTool
from bokeh.transform import factor_cmap, factor_mark
from bokeh.resources import CDN
from datetime import datetime
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
	df['_created']=pd.to_datetime(df['_created'],errors='coerce')
	for index, row in df.iterrows():
		df.loc[index,'Project Type']=row['formData']['fields'][0]['value']
		df.loc[index,'Conditioned_Square_Footage']=row['formData']['fields'][2]['value']
		df.loc[index,'Garage_Square_Footage']=row['formData']['fields'][3]['value']
		df.loc[index,'Other_Square_Footage']=row['formData']['fields'][4]['value']
		df.loc[index,'Preapproval Datetime']=datetime.fromisoformat(row['preReview']['history'][-1]['dateReviewed']) if row['preReview']['history'] else pd.NaT
		df.loc[index,'Final Approval Datetime']=datetime.fromisoformat(row['finalReview']['history'][-1]['dateReviewed']) if row['finalReview']['history'] else pd.NaT
	# for index, row in df.iterrows():
	# 	df.loc[index,'Preapproval Time']=np.busday_count(row['_created'],row['Preapproval Datetime'],weekmask=[1,1,1,1,0,0,0]) if row['Preapproval Datetime'] is not pd.NaT else np.nan
	# 	df.loc[index, 'Final Approval Time']=np.busday_count(row['Preapproval Datetime'],row['Final Approval Datetime'],weekmask=[1,1,1,1,0,0,0]) if row['Final Approval Datetime'] is not pd.NaT else np.nan
	df['Conditioned_Square_Footage']=df['Conditioned_Square_Footage'].astype(float)
	df['Garage_Square_Footage']=df['Garage_Square_Footage'].astype(float)
	df['Other_Square_Footage']=df['Other_Square_Footage'].astype(float)
	df['Total Square Footage']=df['Conditioned_Square_Footage']+df['Garage_Square_Footage']+df['Other_Square_Footage']
	df['Preapproval Time']=df['Preapproval Datetime']-df['_created']
	fig=figure(title='Total Square Footage', x_axis_type='datetime')
	source=ColumnDataSource(df)
	fig.scatter(x="_created",
				y="Total Square Footage",
				source=source,
				size=10,
				color=factor_cmap('Project Type','Category20_{}'.format(len(list(df['Project Type']))),list(df['Project Type'])),
				legend_group="Project Type")
	fig.add_layout(fig.legend[0], "above")
	fig.legend.ncols=int(len(df['Project Type'].unique())/2)
	fig.legend.title="Project Type"
	hover=HoverTool(tooltips=[('Permit Number','@permitNumber'),
							  ('Conditioned Square Footage','@Conditioned_Square_Footage{0,0}'),
							  ('Garage Square Footage','@Garage_Square_Footage{0,0}'),
							  ('Other Square Footage','@Other_Square_Footage{0,0}')])
	fig.add_tools(hover)
	return render_template('index.html',title='Home',fig=file_html(fig,CDN,"Plot"))