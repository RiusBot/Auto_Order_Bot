# import re
# import time
# import easyocr
# import logging
# import numpy as np
# from PIL import Image
# reader = easyocr.Reader(['en'])


# def upper_right_symbol_recognition(img):
#     img = np.array(img)
#     w, h, c = img.shape
#     right = int(w * 0.1)
#     bottom = int(h * 0.02)
#     img = img[:bottom, :right]
#     result = reader.readtext(img, detail=False)
#     return set(result)


# def post_process(results):
#     tmp = []
#     for i in results:
#         for j in i.split():
#             j = re.compile('[^a-zA-Z0-9]').sub('', j)
#             if j:
#                 tmp.append(j.upper())
#     return list(set(tmp))


# def image_recognize(path):
#     st = time.time()
#     img = Image.open(path)
#     results = set()
#     results.update(upper_right_symbol_recognition(img))
#     results = post_process(results)
#     logging.info(f"Image recognition took {time.time()-st} second.")
#     return results
