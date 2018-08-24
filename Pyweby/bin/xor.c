#include "C:\Python37\include\Python.h"
#include <stdio.h>
#include <string.h>


//#define key     "ayongwifisssssssdasasda3434asdasada"   //加密密钥
#define shift_len       13    //字符位移

//加密
int encrypt(char *string, char *out, int outlen,char *key)
{
	if (!string)
		return -1;
	if (!out || !outlen)
		return -1;
	int i, j = 0;
	int maxlen;
	if (strlen(string) > outlen)
		maxlen = outlen;
	else
		maxlen = strlen(string);
	for (i = 0; i< maxlen; i++)
	{
		for (j = 0; j < strlen(key); j++){
			out[i] = (string[i] + shift_len) ^ key[j];
		}
	}
	return 0;
}

//解密
int decrypt(char *str, char *plaintext, int plaintextLen,char *key)
{
	if (!str || !plaintext || !plaintextLen)
	{
		return -1;
	}
	int i, j = 0;
	int maxlen;
	if (strlen(str) > plaintextLen)
		maxlen = plaintextLen;
	else
		maxlen = strlen(str);
	for (i = 0; i< maxlen; i++)
	{
		for (j = 0; j < strlen(key); j++){
			plaintext[i] = str[i] ^ key[j];
			plaintext[i] = plaintext[i] - shift_len;
		}
	}
	return 0;

}
/*

int main()
{
	int i = 0;
	char string[128] = "helloworldsssssxcx&xxxx=ssssssssssssadaafafa";
	char new[128];

	printf("have input:[%s]\n", string);
	memset(new, 0, sizeof(new));

	encrypt(string, new, sizeof(new));
	for (i = 0; i < sizeof(new); i++){
		printf("%0X", new[i]);
	}

	printf("new:%s,%d\n", new, strlen(new));
	//jiemi
	memset(string, 0, sizeof(string));

	decrypt(new, string, sizeof(new));
	printf("string:%s,%d\n", string, strlen(string));
	getchar();
}
*/

static PyObject *_encrypt(PyObject *self, PyObject *args){
	int i;
	PyObject *string, *key;
	char new[32];
	if (!(PyArg_ParseTuple(args, "ss", &string,&key))){
		return NULL;
	}
	//char *new;
	//memcpy(&new,0,i);
	encrypt(string, new, sizeof(new),key);

	return (PyObject*)Py_BuildValue("s", new);
}

static PyObject *_decrypt(PyObject *self, PyObject *args){
	int i;
	PyObject *string, *key;
	char new[32];
	if (!(PyArg_ParseTuple(args, "ss", &string, &key))){
		return NULL;
	}
	decrypt(string, new, sizeof(new), key);
	return (PyObject*)Py_BuildValue("s", new);
}

static PyMethodDef DemoMethods[] = {
	{ "_encrypt", // python method name
	_encrypt, // matched c function name
	METH_VARARGS, /* a flag telling the interpreter the calling convention to be used for the C function. */
	"XOR." },
	{ "_decrypt", // python method name
	_decrypt, // matched c function name
	METH_VARARGS, /* a flag telling the interpreter the calling convention to be used for the C function. */
	"XOR." },
	{ NULL, NULL, 0, NULL }        /* Sentinel */
};

static struct PyModuleDef demomodule = {
	PyModuleDef_HEAD_INIT,
	"demo",   /* name of module */
	NULL, /* module documentation, may be NULL */
	-1,       /* size of per-interpreter state of the module,
			  or -1 if the module keeps state in global variables. */
	DemoMethods
};

PyMODINIT_FUNC PyInit_demo(void)
{
	return PyModule_Create(&demomodule);
}