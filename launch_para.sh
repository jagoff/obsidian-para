#!/bin/bash

# PARA System Launcher Panel

function show_menu() {
  clear
  echo "🗂️  PARA System - Panel de Lanzamiento"
  echo "--------------------------------------"
  echo "1) Dashboard web (Gradio)"
  echo "2) Monitor en terminal"
  echo "3) Clasificar notas (Inbox/Archive)"
  echo "4) Refactorizar Archive"
  echo "5) Exportar dataset de fine-tuning"
  echo "6) Revisión/corrección de feedback"
  echo "7) Ver logs"
  echo "0) Salir"
  echo "--------------------------------------"
}

while true; do
  show_menu
  read -p "Selecciona una opción [0-7]: " opt
  case $opt in
    1)
      echo "Lanzando dashboard web..."
      source venv/bin/activate && python para_dashboard.py
      read -p "Presiona Enter para volver al panel..."
      ;;
    2)
      echo "Lanzando monitor en terminal..."
      source venv/bin/activate && python para_cli.py monitor
      read -p "Presiona Enter para volver al panel..."
      ;;
    3)
      echo "Clasificación de notas (Inbox/Archive)..."
      source venv/bin/activate && python para_cli.py classify
      read -p "Presiona Enter para volver al panel..."
      ;;
    4)
      echo "Refactorización de Archive..."
      source venv/bin/activate && python para_cli.py refactor
      read -p "Presiona Enter para volver al panel..."
      ;;
    5)
      echo "Exportando dataset de fine-tuning..."
      source venv/bin/activate && python para_cli.py export-finetune-dataset
      read -p "Presiona Enter para volver al panel..."
      ;;
    6)
      echo "Revisión/corrección de feedback..."
      source venv/bin/activate && python para_cli.py review-feedback
      read -p "Presiona Enter para volver al panel..."
      ;;
    7)
      echo "Mostrando logs recientes..."
      tail -n 40 logs/para.log | less
      ;;
    0)
      echo "¡Hasta luego!"
      exit 0
      ;;
    *)
      echo "Opción inválida. Intenta de nuevo."
      ;;
  esac
done
