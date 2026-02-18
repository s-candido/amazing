from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

# Import the recommendation function from the local module
from recommandation_system import get_similar_items

app = FastAPI(title="Item-Based Recommendation API")


class SimilarRequest(BaseModel):
	n: Optional[int] = 5
	threshold: Optional[float] = 0.5


@app.get("/health")
async def health():
	return {"status": "ok"}


@app.get("/similar/{product_id}")
async def similar(product_id: str, n: int = 5, threshold: float = 0.5):
	"""Return similar items for a given product_id.

	Query params:
	- n: number of similar items to return (default 5)
	- threshold: similarity threshold for switching to fallback (default 0.5)
	"""
	try:
		result = get_similar_items(product_id, n=n, threshold=threshold)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

	# If the function returned a string (error message), surface as 404 or message
	if isinstance(result, str):
		raise HTTPException(status_code=404, detail=result)

	# Convert DataFrame-like result to JSON-serializable list
	try:
		# Some results may be pandas DataFrame-like objects
		import pandas as pd
		if isinstance(result, pd.DataFrame):
			df = result.reset_index()
			# ensure index column is named consistently
			if df.columns[0] != 'product_id':
				df = df.rename(columns={df.columns[0]: 'product_id'})
			return {"product_id": product_id, "recommendations": df.to_dict(orient='records')}
	except Exception:
		pass

	# Fallback: return raw result
	return {"product_id": product_id, "recommendations": result}


if __name__ == "__main__":
	uvicorn.run("api_reco_sys:app", host="0.0.0.0", port=8080, log_level="info")


