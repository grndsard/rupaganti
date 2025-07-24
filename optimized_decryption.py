def decrypt_file_aes(encrypted_data):
    """Decrypt file data using AES-256 encryption with chunked processing for large files"""
    try:
        # Extract IV from the beginning of the encrypted data
        iv = encrypted_data[:16]
        actual_encrypted_data = encrypted_data[16:]
        
        # For large files, use a more efficient approach with less memory overhead
        if len(actual_encrypted_data) > 10 * 1024 * 1024:  # 10MB
            # Process in chunks for large files
            chunk_size = 1024 * 1024  # 1MB chunks
            cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(iv), backend=backend)
            decryptor = cipher.decryptor()
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
            
            # Process all but the last chunk
            result = bytearray()
            for i in range(0, len(actual_encrypted_data) - chunk_size, chunk_size):
                chunk = actual_encrypted_data[i:i+chunk_size]
                result.extend(decryptor.update(chunk))
            
            # Process the last chunk with unpadding
            last_chunk = actual_encrypted_data[-(len(actual_encrypted_data) % chunk_size or chunk_size):]
            decrypted_last_chunk = decryptor.update(last_chunk) + decryptor.finalize()
            result.extend(unpadder.update(decrypted_last_chunk) + unpadder.finalize())
            
            return bytes(result)
        else:
            # For smaller files, use the simpler approach
            cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(iv), backend=backend)
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(actual_encrypted_data) + decryptor.finalize()
            
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
            return unpadder.update(padded_data) + unpadder.finalize()
    except Exception as e:
        logger.error(f"AES decryption error: {str(e)}")
        raise