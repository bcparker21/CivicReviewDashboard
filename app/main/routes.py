from flask import render_template, Response,render_template_string
from bokeh.plotting import figure, show
from bokeh.embed import components, file_html
from bokeh.io import output_notebook
from bokeh.models import ColumnDataSource, Tooltip, HoverTool, RangeTool
from bokeh.transform import factor_cmap, factor_mark
from bokeh.resources import CDN
from bokeh.layouts import column
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import geopandas as gpd
import seaborn as sns
import requests, io, base64, os
from app.main import bp

api_key=os.getenv('cr_api_key')
api_key_lu=os.getenv('cr_api_key_lu')
base_url='https://api.civicreview.com/public'
all_permits_url='https://api.civicreview.com/public/v1/permits'
params={'Authorization':'Bearer {}'.format(api_key)}
params_lu={'Authorization':'Bearer {}'.format(api_key_lu)}
permit_url='https://api.civicreview.com/public/v1/permits?permitTypes[]={}'
building_permit_id='69850079f7872620069534e1'
lu_id='69656256873619e961314ebf'
permit_params={'Authorization':'Bearer {}'.format(api_key),'isActive':'true','permitTypes':building_permit_id}
permit_params_lu={'Authorization':'Bearer {}'.format(api_key_lu),'isActive':'true','permitTypes':lu_id}
sns.set_theme(style='whitegrid')

@bp.route('/')
@bp.route('/index')
def index():
# Building Permits
# Pull Data
	response=requests.get(permit_url.format('{}&isActive=true'.format(building_permit_id)),headers=permit_params).json()
	df=pd.DataFrame(response)
# Manipulate to usable data
	df['_created']=pd.to_datetime(df['_created'],errors='coerce')
	df['Plan Review Days']=0
	df['Response Days']=0
	df['Inspection Scheduled Days']=0
	df['Between Inspection Days']=0
	for index, row in df.iterrows():
		for i in range(len(row['formData']['fields'])):
			df.loc[index,row['formData']['fields'][i]['label']]=row['formData']['fields'][i]['value']
		df.loc[index,'Preapproval Datetime']=datetime.fromisoformat(row['preReview']['history'][-1]['dateReviewed']) if row['preReview']['history'] else pd.NaT
		df.loc[index,'Final Approval Datetime']=datetime.fromisoformat(row['finalReview']['history'][-1]['dateReviewed']) if row['finalReview']['history'] else pd.NaT
	for index, row in df.iterrows():
		df.loc[index,'Preapproval Time']=np.busday_count(row['_created'].date(),row['Preapproval Datetime'].date()) if row['Preapproval Datetime'] is not pd.NaT else np.nan
		df.loc[index, 'Final Approval Time']=np.busday_count(row['Preapproval Datetime'].date(),row['Final Approval Datetime'].date()) if row['Final Approval Datetime'] is not pd.NaT else np.nan
		if df.loc[index,'planReviews']:
			submissions=df.loc[index,'planReviews'][0]['submissions']
			for i in range(len(submissions)):
				start=np.datetime64(submissions[i]['_created']).astype(datetime)
				start=datetime.date(start)
				end=np.datetime64(submissions[i]['_updated']).astype(datetime)
				end=datetime.date(end)
				prev_sub=np.datetime64(submissions[i-1]['_updated']).astype(datetime)
				prev_sub=datetime.date(prev_sub)
				submissions[i]['Plan Review Days']=int(np.busday_count(start,end))
				submissions[i]['Response Days']=int(np.busday_count(start,np.datetime64(prev_sub))) if int(np.busday_count(start,np.datetime64(prev_sub)))>0 else 0
				df.loc[index,'Plan Review Days']=df.loc[index,'Plan Review Days']+submissions[i]['Plan Review Days']
				df.loc[index,'Response Days']=df.loc[index,'Response Days']+submissions[i]['Response Days']
				df.loc[index,'Plan Reviews']=len(submissions)
		if df.loc[index,'inspections']:
			inspections=df.loc[index,'inspections']
			for i in range(len(inspections)):
				start=np.datetime64(inspections[i]['_created']).astype(datetime)
				start=datetime.date(start)
				end=np.datetime64(inspections[i]['inspectionDate']).astype(datetime)
				end=datetime.date(end)
				prev_inspection=np.datetime64(inspections[i-1]['inspectionDate']).astype(datetime)
				prev_inspection=datetime.date(prev_inspection)
				inspections[i]['Inspection Scheduled Days']=int(np.busday_count(start,end))
				if end >= prev_inspection:
					inspections[i]['Between Inspection Days']=int(np.busday_count(prev_inspection, end))
					df.loc[index,'Between Inspection Days']=df.loc[index,'Between Inspection Days']+inspections[i]['Between Inspection Days']
				df.loc[index,'Inspection Scheduled Days']=df.loc[index,'Inspection Scheduled Days']+inspections[i]['Inspection Scheduled Days']
				df.loc[index,'Number of Inspections']=len(inspections)
	df['Average Plan Review Days']=df['Plan Review Days']/df['Plan Reviews']
	df['Average Response Days']=df['Response Days']/df['Plan Reviews']
	df['Average Inspection Scheduled Days']=df['Inspection Scheduled Days']/df['Number of Inspections']
	df['Average Between Inspection Days']=df['Between Inspection Days']/df['Number of Inspections']
	df.replace('',0,inplace=True)
	df.rename(columns={'Other Covered/Non-Conditioned Space Sq Footage':'Other_Covered_or_Non_Conditioned_Space_Sq_Footage',
					   'Conditioned Space Sq Footage': 'Conditioned_Space_Sq_Footage',
					   'Garage Sq Footage':'Garage_Sq_Footage',
					   'Site Address':'Site_Address'}, inplace=True)
	df['Conditioned_Space_Sq_Footage']=df['Conditioned_Space_Sq_Footage'].astype(float)
	df['Garage_Sq_Footage']=df['Garage_Sq_Footage'].astype(float)
	df['Other_Covered_or_Non_Conditioned_Space_Sq_Footage']=df['Other_Covered_or_Non_Conditioned_Space_Sq_Footage'].astype(float)
	df['Total Square Footage']=df['Conditioned_Space_Sq_Footage'].fillna(0)+df['Garage_Sq_Footage'].fillna(0)+df['Other_Covered_or_Non_Conditioned_Space_Sq_Footage'].fillna(0)

# Square Footage Scatter
	fig=figure(x_axis_type='datetime')
	source=ColumnDataSource(df)
	fig.scatter(x="_created",
				y="Total Square Footage",
				source=source,
				size=10,
				color=factor_cmap('Select Project Type','Category20_{}'.format(len(list(df['Select Project Type'].unique()))),list(df['Select Project Type'].unique())),
				legend_group="Select Project Type")
	fig.add_layout(fig.legend[0], "above")
	fig.legend.ncols=int(len(df['Select Project Type'].unique())/2)
	fig.legend.title="Project Type"
	hover=HoverTool(tooltips=[('Permit Number','@permitNumber'),
							  ('Conditioned Square Footage','@Conditioned_Space_Sq_Footage{0,0}'),
							  ('Garage Square Footage','@Garage_Sq_Footage{0,0}'),
							  ('Other Square Footage','@Other_Covered_or_Non_Conditioned_Space_Sq_Footage{0,0}'),
							  ('Address','@Site_Address')])
	fig.add_tools(hover)
	select=figure(title='Drag the middle and edges of the selection box to change the range above.',
				  height=130,
				  y_range=fig.y_range,
				  x_axis_type='datetime',
				  y_axis_type=None,
				  tools="",
				  toolbar_location=None)
	range_tool=RangeTool(x_range=fig.x_range)
	range_tool.overlay.fill_color="navy"
	range_tool.overlay.fill_alpha=0.2
	select.scatter('_created','Total Square Footage',source=source)
	select.ygrid.grid_line_color=None
	select.add_tools(range_tool)
	tsf_plot=column(fig,select)
# violin plot
	vfig, vax=plt.subplots(figsize=(5,6))
	sns.violinplot(y='Select Project Type',
				   x='Final Approval Time',
				   data=df,
				   ax=vax,
				   inner='point')
	vax.set_xlabel='Days'
	vax.set_ylabel='Project Type'
	img=io.BytesIO()
	vfig.savefig(img,format='png',bbox_inches='tight')
	plt.close(vfig)
	img.seek(0)
	img_base64=base64.b64encode(img.read()).decode('utf-8')
	vfig_out='<img src="data:image/png;base64,{}">'.format(img_base64)

	counts=pd.DataFrame(df.groupby('Select Project Type').count()['_id'])
	counts.reset_index(inplace=True)
	counts.rename(columns={'Select Project Type':'Project Type',
						   '_id':'Count'},
				  inplace=True,errors="raise")
# Land Use
# Pull Data
	lu_response=requests.get(permit_url.format('{}&isActive=true'.format(lu_id)),headers=permit_params_lu).json()
	lu_df=pd.DataFrame(lu_response)
# Manipulate into Usable Data
	for index, row in lu_df.iterrows():
		for i in range(len(row['formData']['fields'])):
			lu_df.loc[index,row['formData']['fields'][i]['label']]=row['formData']['fields'][i]['value']
		# start=np.datetime64(row['formData']['dateSubmitted']).astype(datetime)
		# end=np.datetime64(row['finalReview']['history'][0]['dateReviewed']).astype(datetime if len(row['finalReview'])>0 else np.nan)
		# lu_df.loc[index,'Final Approval Time']=np.busday_count(start.date(),end.date()) if end is not pd.NaT else np.nan
	lu_counts=pd.DataFrame(lu_df.groupby('Permit Type (select all that apply)').count()['_id'])
	lu_counts.reset_index(inplace=True)
	lu_counts['Permit Type (select all that apply)']=lu_counts['Permit Type (select all that apply)'].str.strip("[]'\"")
	lu_counts_fig=figure(y_range=lu_counts['Permit Type (select all that apply)'],title='Land Use Application Types')
	lu_counts_fig.hbar(y=lu_counts['Permit Type (select all that apply)'].tolist(),right=lu_counts['_id'].tolist(),height=.6)
	created=lu_df['formData']
	return render_template('index.html',
							title='Community Development Dashboard',
							fig=file_html(tsf_plot,CDN,"Plot"),
							preapproval_time=df['Preapproval Time'].mean(),
							preapproval_time_median=df['Preapproval Time'].median(),
							plan_review_time=df['Average Plan Review Days'].mean(),
							plan_review_time_median=df['Average Plan Review Days'].median(),
							num_reviews=df['Plan Reviews'].mean(),
							num_reviews_median=df['Plan Reviews'].median(),
							resubmittal_time=df['Average Response Days'].mean(),
							resubmittal_time_median=df['Average Response Days'].median(),
							vfig=vfig_out,
							final_approval_time=df['Final Approval Time'].mean(),
							final_approval_time_median=df['Final Approval Time'].median(),
							inspection_scheduled_days=df['Average Inspection Scheduled Days'].mean(),
							days_between_inspections=df['Average Between Inspection Days'].mean(),
							number_of_inspections=df['Number of Inspections'].mean(),
							counts=counts.to_html(classes="table",index=False),
							lu_counts_fig=file_html(lu_counts_fig,CDN,"Plot"),
							data=lu_df.to_html()
							)
