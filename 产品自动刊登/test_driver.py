from selenium import webdriver
# 如果不报错且浏览器弹出来，说明驱动没问题
driver = webdriver.Edge()
print("驱动正常")
driver.quit()