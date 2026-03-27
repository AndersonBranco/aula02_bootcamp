# #### Inteiros (`int`)

# 1. Escreva um programa que soma dois números inteiros inseridos pelo usuário.
#numero_01 = int(input("Digite o primeiro número inteiro: "))
#numero_02 = int(input("Digite o segundo número inteiro: "))
#soma = numero_01 + numero_02
#print(f"A soma dos números {numero_01} e {numero_02} é: {soma}")

# 2. Crie um programa que receba um número do usuário e calcule o resto da divisão desse número por 5.
#numero = int(input("Digite um número inteiro: "))
#resto = numero % 5
#print(f"O resto da divisão de {numero} por 5 é: {resto}")

# 3. Desenvolva um programa que multiplique dois números fornecidos pelo usuário e mostre o resultado.
#numero_01 = float(input("Digite o primeiro número: "))
#numero_02 = float(input("Digite o segundo número: "))
#resultado = numero_01 * numero_02
#print(f"O resultado da multiplicação dos números {numero_01} e {numero_02} é: {resultado}")

# 4. Faça um programa que peça dois números inteiros e imprima a divisão inteira do primeiro pelo segundo.
#numero_01 = int(input("Digite o primeiro número inteiro: "))
#numero_02 = int(input("Digite o segundo número inteiro: "))
#divisao_inteira = numero_01 // numero_02
#print(f"A divisão inteira de {numero_01} por {numero_02} é: {divisao_inteira}")

# 5. Escreva um programa que calcule o quadrado de um número fornecido pelo usuário.
# #### Números de Ponto Flutuante (`float`)
#numero_01 = float(input("Digite um número: "))
#quadrado = numero_01 ** 2
#print(f"O quadrado do número {numero_01} é: {quadrado}")

# 6. Escreva um programa que receba dois números flutuantes e realize sua adição.

#numero_01 = float(input("Digite o primeiro número: "))
#numero_02 = float(input("Digite o segundo número: "))
#soma = numero_01 + numero_02
#print(f"A soma dos números {numero_01} e {numero_02} é: {soma}")


# 7. Crie um programa que calcule a média de dois números flutuantes fornecidos pelo usuário.

#numero_01 = float(input("Digite o primeiro número: "))
#numero_02 = float(input("Digite o segundo número: "))
#media = (numero_01 + numero_02) / 2
#print(f"A média dos números {numero_01} e {numero_02} é: {media}")


# 8. Desenvolva um programa que calcule a potência de um número (base e expoente fornecidos pelo usuário).
#numero_01 = float(input("Digite a base: "))
#expoente = float(input("Digite o expoente: "))      
#potencia = numero_01 ** expoente
#print(f"O resultado de {numero_01} elevado a {expoente} é: {potencia}") 


# 9. Faça um programa que converta a temperatura de Celsius para Fahrenheit.
#celsius = float(input("Digite a temperatura em Celsius: "))
#fahrenheit = (celsius * 9/5) + 32
#print(f"A temperatura de {celsius}°C é equivalente a {fahrenheit}°F.")


# 10. Escreva um programa que calcule a área de um círculo, recebendo o raio como entrada.
#import math
#raio = float(input("Digite o raio do círculo: "))
#area = math.pi * (raio ** 2)
#print(f"A área do círculo com raio {raio} é: {area:.2f}")

# #### Strings (`str`)

# 11. Escreva um programa que receba uma string do usuário e a converta para maiúsculas.
#texto = input("Digite uma string: ")
#print(f"String em maiúsculas: {texto.upper()}")


# 12. Crie um programa que receba o nome completo do usuário e imprima o nome com todas as letras minúsculas.
#nome = input("Digite seu nome completo: ")
# print(f"Nome em minúsculas: {nome.lower()}")

# 13. Desenvolva um programa que peça ao usuário para inserir uma frase e, em seguida, imprima esta frase sem espaços em branco no início e no final.
#frase = input("Digite uma frase: ")
#print(f"Frase sem espaços em branco: '{frase.strip()}'")

# 14. Faça um programa que peça ao usuário para digitar uma data no formato "dd/mm/aaaa" e, em seguida, imprima o dia, o mês e o ano separadamente.
#data = input("Digite uma data no formato dd/mm/aaaa: ")
#dia, mes, ano = data.split('/')
#print(f"Dia: {dia}")
#print(f"Mês: {mes}")
#print(f"Ano: {ano}")


# 15. Escreva um programa que concatene duas strings fornecidas pelo usuário.
#string_01 = input("Digite a primeira string: ")
#string_02 = input("Digite a segunda string: ")      
#string_concatenada = string_01 + string_02
#print(f"String concatenada: {string_concatenada}")

# 16. Escreva um programa que avalie duas expressões booleanas inseridas pelo usuário e retorne o resultado da operação AND entre elas.
#expressao_01 = input("Digite a primeira expressão booleana (True/False): ")
#expressao_02 = input("Digite a segunda expressão booleana (True/False): ")
#resultado_and = (expressao_01 == "True") and (expressao_02 == "True")
#print(f"O resultado da operação AND entre as expressões é: {resultado_and}")    


# 17. Crie um programa que receba dois valores booleanos do usuário e retorne o resultado da operação OR.
#booleano_01 = input("Digite o primeiro valor booleano (True/False): ")
#booleano_02 = input("Digite o segundo valor booleano (True/False): ")   
#resultado_or = (booleano_01 == "True") or (booleano_02 == "True")
#print(f"O resultado da operação OR entre os valores booleanos é: {resultado_or}")

# 18. Desenvolva um programa que peça ao usuário para inserir um valor booleano e, em seguida, inverta esse valor.
#booleano = input("Digite um valor booleano (True/False): ")
#if booleano == "True":
 #   booleano_invertido = "False"    
#elif booleano == "False":
#    booleano_invertido = "True"
#else:
 #   booleano_invertido = "Valor inválido. Por favor, insira 'True' ou 'False'."
#print(f"O valor booleano invertido é: {booleano_invertido}")    


# 19. Faça um programa que compare se dois números fornecidos pelo usuário são iguais.
#numero_01 = float(input("Digite o primeiro número: "))
#numero_02 = float(input("Digite o segundo número: "))
#sao_iguais = numero_01 == numero_02
#print(f"Os números {numero_01} e {numero_02} são iguais? {sao_iguais}")

# 20. Escreva um programa que verifique se dois números fornecidos pelo usuário são diferentes.
#numero_01 = float(input("Digite o primeiro número: "))
#numero_02 = float(input("Digite o segundo número: "))
#sao_diferentes = numero_01 != numero_02
#print(f"Os números {numero_01} e {numero_02} são diferentes? {sao_diferentes}")


# #### try-except e if

# 21: Conversor de Temperatura
# 22: Verificador de Palíndromo
# 23: Calculadora Simples
# 24: Classificador de Números
# 25: Conversão de Tipo com Validação

