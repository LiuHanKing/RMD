from selenium import webdriver
from selenium.webdriver.common.by import By
import time

# 初始化浏览器
driver = webdriver.Chrome()

# 打开网盘登录页面
driver.get('https://example.com/login')

# 输入用户名和密码
username = driver.find_element(By.ID, 'username')
password = driver.find_element(By.ID, 'password')
username.send_keys('your_username')
password.send_keys('your_password')

# 点击登录按钮
login_button = driver.find_element(By.ID, 'login-button')
login_button.click()

# 等待页面加载
time.sleep(5)

# 找到下载链接并点击
download_link = driver.find_element(By.LINK_TEXT, 'Download')
download_link.click()

# 关闭浏览器
driver.quit()