from fastapi import Request


async def evaluate(credit_template:list[None],request:Request):

    #credit_template - ['A',+,"B",'-','C',<,D]
    STOPPING_POSITIONS = ['<','=','>','<=','>=','!=']
    OPERATORS = ['+','-','*','/','//','%']

    i=0
    left_parameter=0
    right_parameter=0
    left=0
    right=0

    while i < len(credit_template):

        if credit_template[i] in STOPPING_POSITIONS:
            break
        
        if credit_template[i] not in OPERATORS:
            i=i+1
        left_parameter=credit_template[i-1]
        right_parameter=credit_template[i+1]

        #get the customer's value
        