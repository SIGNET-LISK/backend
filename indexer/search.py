from services.verifier import ANNVerifier

# Global instance
verifier = ANNVerifier()

def get_verifier():
    return verifier
