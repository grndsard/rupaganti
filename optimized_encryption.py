def encrypt_file_aes(file_data):
    """Encrypt file data using AES-256 encryption with hardware acceleration"""
    try:
        # For large files, use a more efficient approach with less memory overhead
        if len(file_data) > 10 * 1024 * 1024:  # 10MB
            # Process in chunks for large files
            chunk_size = 1024 * 1024  # 1MB chunks
            padder = padding.PKCS7(algorithms.AES.block_size).padder()
            cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(ENCRYPTION_IV), backend=backend)
            encryptor = cipher.encryptor()
            
            # Process all but the last chunk
            result = bytearray()
            for i in range(0, len(file_data) - chunk_size, chunk_size):
                chunk = file_data[i:i+chunk_size]
                result.extend(encryptor.update(chunk))
            
            # Process the last chunk with padding
            last_chunk = file_data[-(len(file_data) % chunk_size or chunk_size):]
            padded_last_chunk = padder.update(last_chunk) + padder.finalize()
            result.extend(encryptor.update(padded_last_chunk) + encryptor.finalize())
            
            # Prepend IV to the encrypted data for decryption later
            return ENCRYPTION_IV + bytes(result)
        else:
            # For smaller files, use the simpler approach
            padder = padding.PKCS7(algorithms.AES.block_size).padder()
            padded_data = padder.update(file_data) + padder.finalize()
            
            cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(ENCRYPTION_IV), backend=backend)
            encryptor = cipher.encryptor()
            
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # Prepend IV to the encrypted data for decryption later
            return ENCRYPTION_IV + encrypted_data
    except Exception as e:
        logger.error(f"AES encryption error: {str(e)}")
        raise