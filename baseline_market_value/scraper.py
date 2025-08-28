import requests
from bs4 import BeautifulSoup

# This function is used to extract the Drivers Full Name
def get_driver_name(url,driver):
    response=requests.get(url)
    soup=BeautifulSoup(response.text,'html.parser')

    h1_tags=soup.find_all('h1')

    for h1 in h1_tags:
        if driver in h1.get_text():
            return h1.get_text(strip=True)
    return None

# This function is used to extract the drivers particular details like Salary etc.
def get_details(url,target_detail):
    response=requests.get(url)
    soup=BeautifulSoup(response.text,'html.parser')

    dt_tags=soup.find_all('dt')

    for dt in dt_tags:
        if target_detail in dt.get_text():
            dd=dt.find_next_sibling('dd')
            if dd:
                return dd.get_text(strip=True)
            else:
                return None
    return None

# This function is used to calculate the Baseline Net Value of the Driver
def get_baseline_market_value(url,driver):
    salary_winnings=get_details(url,"Salary/Winnings")
    if salary_winnings:
        salary_value=float(salary_winnings.replace(" ","").replace("$","").split("M")[0])
    else:
        salary_value=0
    endorsements=get_details(url,"Endorsements")
    if endorsements:
        endorsement_value=float(endorsements.replace(" ","").replace("$","").split("M")[0])
    else:
        endorsement_value=0
    total=salary_value+endorsement_value
    return f"${int(total)} M"

# Drivers

# Driver-1
url="https://www.forbes.com/profile/max-verstappen/"
driver='Max Verstappen'
print("Driver Name:",get_driver_name(url,driver))
target_detail="Salary/Winnings"
print("Salary/Winnings:",get_details(url,target_detail))
target_detail="Endorsements"
print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",get_baseline_market_value(url,driver))
print("-"*50)

# Driver-2
url="https://www.forbes.com/profile/lewis-hamilton/"
driver='Lewis Hamilton'
print("Driver Name:",get_driver_name(url,driver))
target_detail="Salary/Winnings"
print("Salary/Winnings:",get_details(url,target_detail))
target_detail="Endorsements"
print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",get_baseline_market_value(url,driver))
print("-"*50)

# Driver-3
url="https://www.forbes.com/profile/oscar-piastri/"
driver='Oscar Piastri'
print("Driver Name:",get_driver_name(url,driver))
target_detail="Salary/Winnings"
print("Salary/Winnings:",get_details(url,target_detail))
target_detail="Endorsements"
print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",get_baseline_market_value(url,driver))
print("-"*50)

# Driver-4
url="https://www.forbes.com/profile/lando-norris/"
driver='Lando Norris'
print("Driver Name:",get_driver_name(url,driver))
target_detail="Salary/Winnings"
print("Salary/Winnings:",get_details(url,target_detail))
target_detail="Endorsements"
print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",get_baseline_market_value(url,driver))
print("-"*50)

# Driver-5
url="https://www.forbes.com/profile/charles-leclerc/"
driver='Charles Leclerc'
print("Driver Name:",get_driver_name(url,driver))
target_detail="Salary/Winnings"
print("Salary/Winnings:",get_details(url,target_detail))
target_detail="Endorsements"
print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",get_baseline_market_value(url,driver))
print("-"*50)

# Driver-6
url="https://www.forbes.com/profile/fernando-alonso/"
driver='Fernando Alonso'
print("Driver Name:",get_driver_name(url,driver))
target_detail="Salary/Winnings"
print("Salary/Winnings:",get_details(url,target_detail))
target_detail="Endorsements"
print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",get_baseline_market_value(url,driver))
print("-"*50)

# Driver-7
url="https://www.forbes.com/profile/george-russell-1/"
driver='George Russell'
print("Driver Name:",get_driver_name(url,driver))
target_detail="Salary/Winnings"
print("Salary/Winnings:",get_details(url,target_detail))
target_detail="Endorsements"
print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",get_baseline_market_value(url,driver))
print("-"*50)

# Driver-8
url="https://www.forbes.com/profile/pierre-gasly/"
driver='Pierre Gasly'
print("Driver Name:",get_driver_name(url,driver))
target_detail="Salary/Winnings"
print("Salary/Winnings:",get_details(url,target_detail))
target_detail="Endorsements"
print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",get_baseline_market_value(url,driver))
print("-"*50)

# Driver-9
url="https://www.forbes.com/profile/carlos-sainz/"
driver='Carlos Sainz'
print("Driver Name:",get_driver_name(url,driver))
target_detail="Salary/Winnings"
print("Salary/Winnings:",get_details(url,target_detail))
target_detail="Endorsements"
print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",get_baseline_market_value(url,driver))
print("-"*50)

# Driver-10 (Rookie)
# url="https://www.forbes.com/profile/?"
driver='Kimi Antonelli'
print("Driver Name:",driver)
#target_detail="Salary/Winnings"
#print("Salary/Winnings:")
#target_detail="Endorsements"
#print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",'$2 M')
print("-"*50)

# Driver-11 (Rookie)
# url="https://www.forbes.com/profile/?"
driver='Ollie Bearman'
print("Driver Name:",driver)
#target_detail="Salary/Winnings"
#print("Salary/Winnings:")
#target_detail="Endorsements"
#print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",'$0.75 M')
print("-"*50)

# Driver-12 (Rookie)
# url="https://www.forbes.com/profile/?"
driver='Gabriel Bortoleto'
print("Driver Name:",driver)
#target_detail="Salary/Winnings"
#print("Salary/Winnings:")
#target_detail="Endorsements"
#print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",'$1 M')
print("-"*50)

# Driver-13 (2nd year Driver)
# url="https://www.forbes.com/profile/?"
driver='Jack Doohan'
print("Driver Name:",driver)
#target_detail="Salary/Winnings"
#print("Salary/Winnings:")
#target_detail="Endorsements"
#print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",'$1 M')
print("-"*50)

# Driver-14 (2nd year Driver)
# url="https://www.forbes.com/profile/?"
driver='Franco Colapinto'
print("Driver Name:",driver)
#target_detail="Salary/Winnings"
#print("Salary/Winnings:")
#target_detail="Endorsements"
#print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",'$0.75 M')
print("-"*50)

# Driver-15 (Experienced Driver)
# url="https://www.forbes.com/profile/?"
driver='Yuki Tsunoda'
print("Driver Name:",driver)
#target_detail="Salary/Winnings"
#print("Salary/Winnings:")
#target_detail="Endorsements"
#print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",'$0.75 M')
print("-"*50)

# Driver-16 (2nd year Driver)
driver='Liam Lawson'
print("Driver Name:",driver)
#target_detail="Salary/Winnings"
#print("Salary/Winnings:")
#target_detail="Endorsements"
#print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",'$0.375 M')
print("-"*50)

# Driver-17 (Rookie)
driver='Isack Hadjar'
print("Driver Name:",driver)
#target_detail="Salary/Winnings"
#print("Salary/Winnings:")
#target_detail="Endorsements"
#print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",'$0.375 M')
print("-"*50)

# Driver-18 (Experienced Driver)
driver='Lance Stroll'
print("Driver Name:",driver)
#target_detail="Salary/Winnings"
#print("Salary/Winnings:")
#target_detail="Endorsements"
#print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",'$2 M')
print("-"*50)

# Driver-19 (Experienced Driver)
driver='Nico Hulkenberg'
print("Driver Name:",driver)
#target_detail="Salary/Winnings"
#print("Salary/Winnings:")
#target_detail="Endorsements"
#print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",'$7 M')
print("-"*50)

# Driver-20 (Experienced Driver)
driver='Esteban Ocon'
print("Driver Name:",driver)
#target_detail="Salary/Winnings"
#print("Salary/Winnings:")
#target_detail="Endorsements"
#print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",'$6 M')
print("-"*50)

# Driver-21 (Experienced Driver)
driver='Alex Albon'
print("Driver Name:",driver)
#target_detail="Salary/Winnings"
#print("Salary/Winnings:")
#target_detail="Endorsements"
#print("Endorsements:",get_details(url,target_detail))
print("Baseline Value:",'$3 M')
print("-"*50)
