# app/services/model_processor.py
from app.logging_config import get_logger

logger = get_logger(__name__)

class ModelProcessor:
    """
    Model processor that handles the delegation pattern for model processing.
    Provides a unified interface for preprocessing, running, and postprocessing data.
    """
    
    def __init__(self, model_instance):
        self.model = model_instance
        self._validate_model_interface()
    
    def _validate_model_interface(self):
        """Validate that the model has the required interface methods"""
        required_methods = ['preprocess', 'run', 'postprocess']
        missing_methods = []
        
        for method in required_methods:
            if not hasattr(self.model, method) or not callable(getattr(self.model, method)):
                missing_methods.append(method)
        
        if missing_methods:
            model_name = type(self.model).__name__
            missing_str = ', '.join(missing_methods)
            raise ValueError(
                f"Model '{model_name}' is missing required interface methods: {missing_str}. "
                f"Please implement these methods in your model class. "
                f"See the model interface documentation for details."
            )
    
    def process(self, data, device='cpu'):
        """
        Process data through the complete model pipeline.
        
        Args:
            data: Raw session data (DataFrame or other format)
            device: Target device ('cpu' or 'cuda')
            
        Returns:
            Time-domain predictions ready for bout extraction
        """
        try:
            logger.info(f"Processing data through model on device: {device}")
            
            # Step 1: Preprocess data
            preprocessed_data = self.model.preprocess(data)
            logger.debug("Data preprocessing completed")
            
            # Step 2: Run model inference
            raw_predictions = self.model.run(preprocessed_data, device)
            logger.debug("Model inference completed")
            
            # Step 3: Postprocess predictions
            time_domain_predictions = self.model.postprocess(raw_predictions)
            logger.debug("Prediction postprocessing completed")
            
            return time_domain_predictions
            
        except Exception as e:
            logger.error(f"Error in model processing pipeline: {e}")
            raise