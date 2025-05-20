# Dash Application

This project is a Dash application designed for data visualization. It starts by plotting a single recording and is structured to allow for future enhancements, such as dropdown switchers and additional features.

## Project Structure

```
dash-app
├── app
│   ├── __init__.py
│   ├── callbacks.py
│   ├── layout.py
│   ├── utils.py
│   └── data
│       ├── __init__.py
│       └── data_loader.py
├── assets
│   └── styles.css
├── requirements.txt
├── run.py
└── README.md
```

## Installation

To set up the project, follow these steps:

1. Clone the repository:
   ```
   git clone <repository-url>
   cd dash-app
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

To run the Dash application, execute the following command:

```
python run.py
```

The application will start and can be accessed in your web browser at `http://127.0.0.1:8050`.

## Future Enhancements

- Implement a dropdown switcher for selecting different recordings.
- Add more interactive features and visualizations.
- Improve the user interface with additional styling and layout options.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any suggestions or improvements.

## License

This project is licensed under the MIT License. See the LICENSE file for details.